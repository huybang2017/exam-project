from app.application.dto import AnswerChoice, AttemptPolicy, AttemptResult, AttemptView
from app.domain import rules
from app.domain.entities import Attempt, PublicQuestion
from app.domain.errors import ConflictError, DuplicateAttemptError, InvalidError, NotFoundError
from app.domain.ports import Clock, ExamQuestionCache
from app.domain.repositories import UnitOfWork


async def public_questions(
    uow: UnitOfWork, cache: ExamQuestionCache, policy: AttemptPolicy, exam_id: int
) -> tuple[PublicQuestion, ...]:
    """Câu hỏi gửi cho thí sinh (không có đáp án đúng). Đề đã công bố là bất biến nên cache an toàn."""
    if policy.cache_enabled:
        cached = cache.get(exam_id)
        if cached is not None:
            return cached
    questions = await uow.exams.public_questions(exam_id)
    if policy.cache_enabled:
        cache.set(exam_id, questions, policy.cache_ttl_seconds)
    return questions


async def load_own_attempt(uow: UnitOfWork, attempt_id: int, user_id: int) -> Attempt:
    attempt = await uow.attempts.get(attempt_id)
    if attempt is None or attempt.user_id != user_id:
        # Bài của người khác cũng trả "không tìm thấy" để không lộ id nào tồn tại
        raise NotFoundError("Không tìm thấy bài làm")
    return attempt


class AttemptGrader:
    """Chấm điểm và nộp bài, dùng chung cho API nộp bài, WebSocket và vòng quét thu bài."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self.uow, self.clock = uow, clock

    async def submit(self, attempt: Attempt, *, auto: bool = False, at=None) -> Attempt:
        """Nộp đúng một lần (idempotent): nếu đã nộp thì giữ nguyên kết quả."""
        if attempt.is_submitted:
            return attempt
        grade = await self.uow.attempts.grade_inputs(attempt)
        attempt.score = rules.to_ten_scale(grade.earned_points, grade.total_points)
        attempt.submitted_at = at or min(self.clock.now(), attempt.deadline)
        attempt.auto_submitted = auto
        await self.uow.attempts.save(attempt)
        await self.uow.commit()
        return attempt

    async def result(self, attempt: Attempt) -> AttemptResult:
        grade = await self.uow.attempts.grade_inputs(attempt)
        return AttemptResult(attempt, grade.correct_count, grade.total_questions)


class StartAttempt:
    """Bắt đầu làm bài. Gọi lại nhiều lần vẫn trả về cùng một bài làm (idempotent): hỗ trợ F5 và vào lại khi rớt mạng."""

    def __init__(self, uow: UnitOfWork, cache: ExamQuestionCache, clock: Clock, policy: AttemptPolicy) -> None:
        self.uow, self.cache, self.clock, self.policy = uow, cache, clock, policy

    async def execute(self, exam_id: int, user_id: int) -> tuple[AttemptView, bool]:
        """Trả (bài làm, vừa tạo mới hay không)."""
        exam = await self.uow.exams.get(exam_id)
        if exam is None or not exam.is_published:
            raise NotFoundError("Không tìm thấy đề thi")

        existing = await self.uow.attempts.get_for_exam_user(exam_id, user_id)
        if existing is not None:
            return await self._view(existing), False

        now = self.clock.now()
        rules.ensure_window_open(exam, now)
        deadline = rules.compute_deadline(now, exam.duration_minutes, exam.end_time)
        try:
            attempt = await self.uow.attempts.add(Attempt(exam_id, user_id, now, deadline))
            await self.uow.commit()
            created = True
        except DuplicateAttemptError:  # hai request "bắt đầu" đến cùng lúc
            await self.uow.rollback()
            attempt = await self.uow.attempts.get_for_exam_user(exam_id, user_id)
            created = False
        return await self._view(attempt), created

    async def _view(self, attempt: Attempt) -> AttemptView:
        return AttemptView(
            attempt,
            rules.remaining_seconds(attempt, self.clock.now()),
            await public_questions(self.uow, self.cache, self.policy, attempt.exam_id),
            await self.uow.attempts.saved_answers(attempt.id),
        )


class GetAttempt:
    def __init__(self, uow: UnitOfWork, cache: ExamQuestionCache, clock: Clock, policy: AttemptPolicy) -> None:
        self.uow, self.cache, self.clock, self.policy = uow, cache, clock, policy

    async def execute(self, attempt_id: int, user_id: int) -> AttemptView:
        attempt = await load_own_attempt(self.uow, attempt_id, user_id)
        return AttemptView(
            attempt,
            rules.remaining_seconds(attempt, self.clock.now()),
            await public_questions(self.uow, self.cache, self.policy, attempt.exam_id),
            await self.uow.attempts.saved_answers(attempt.id),
        )


class ListMyAttempts:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self.uow, self.clock = uow, clock

    async def execute(self, user_id: int) -> list[AttemptView]:
        now = self.clock.now()
        return [AttemptView(a, rules.remaining_seconds(a, now)) for a in await self.uow.attempts.list_for_user(user_id)]


class SaveAnswers:
    """Tự động lưu đáp án (autosave). Mỗi câu chỉ giữ lựa chọn mới nhất."""

    def __init__(self, uow: UnitOfWork, clock: Clock, policy: AttemptPolicy) -> None:
        self.uow, self.clock, self.policy = uow, clock, policy

    async def execute(self, attempt_id: int, user_id: int, answers: list[AnswerChoice]) -> AttemptView:
        attempt = await load_own_attempt(self.uow, attempt_id, user_id)
        now = self.clock.now()
        rules.ensure_can_save_answers(attempt, now, self.policy.submit_grace_seconds)

        if answers:
            valid = await self.uow.exams.valid_choice_pairs(attempt.exam_id, [a.choice_id for a in answers])
            for a in answers:
                if (a.choice_id, a.question_id) not in valid:
                    raise InvalidError(f"Đáp án {a.choice_id} không thuộc câu {a.question_id} của đề này")
            await self.uow.attempts.upsert_answers(attempt.id, {a.question_id: a.choice_id for a in answers})
            await self.uow.commit()
        return AttemptView(attempt, rules.remaining_seconds(attempt, now))


class SubmitAttempt:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self.uow, self.clock = uow, clock

    async def execute(self, attempt_id: int, user_id: int) -> tuple[AttemptResult, bool]:
        """Trả (kết quả, đây có phải lần nộp đầu tiên không)."""
        attempt = await load_own_attempt(self.uow, attempt_id, user_id)
        first_time = not attempt.is_submitted
        grader = AttemptGrader(self.uow, self.clock)
        await grader.submit(attempt)
        return await grader.result(attempt), first_time


class GetAttemptResult:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self.uow, self.clock = uow, clock

    async def execute(self, attempt_id: int, user_id: int) -> AttemptResult:
        attempt = await load_own_attempt(self.uow, attempt_id, user_id)
        if not attempt.is_submitted:
            raise ConflictError("Bài chưa được nộp")
        return await AttemptGrader(self.uow, self.clock).result(attempt)


class GetAttemptForClock:
    """Dùng cho WebSocket đồng hồ: xác nhận chủ bài làm rồi trả bài (chỉ cần deadline)."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, attempt_id: int, user_id: int) -> Attempt:
        return await load_own_attempt(self.uow, attempt_id, user_id)


class ExpireAttempt:
    """Thu bài một lượt làm đã quá hạn (dùng cho WebSocket khi đồng hồ về 0)."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self.uow, self.clock = uow, clock

    async def execute(self, attempt_id: int) -> Attempt:
        attempt = await self.uow.attempts.get(attempt_id)
        if attempt is None:
            raise NotFoundError("Không tìm thấy bài làm")
        return await AttemptGrader(self.uow, self.clock).submit(attempt, auto=True, at=attempt.deadline)


class AutoSubmitExpiredAttempts:
    """Quét và thu mọi bài quá hạn mà chưa nộp (phòng khi thí sinh đóng trình duyệt)."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self.uow, self.clock = uow, clock

    async def execute(self) -> int:
        grader = AttemptGrader(self.uow, self.clock)
        expired = await self.uow.attempts.list_expired(self.clock.now())
        for attempt in expired:
            await grader.submit(attempt, auto=True, at=attempt.deadline)
        return len(expired)
