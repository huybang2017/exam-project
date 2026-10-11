"""Test use case bằng repository giả: nhanh, không cần PostgreSQL, HTTP hay đồng hồ thật."""
import asyncio
from datetime import timedelta

import pytest

from app.application.dto import AnswerChoice, AttemptPolicy, NewChoice, NewExamItem
from app.application.use_cases.attempts import (
    AutoSubmitExpiredAttempts,
    GetAttempt,
    GetAttemptResult,
    SaveAnswers,
    StartAttempt,
    SubmitAttempt,
)
from app.application.use_cases.auth import Authenticate, Login, RegisterStudent
from app.application.use_cases.exams import CreateExam, GetExamDetail, PublishExam
from app.application.use_cases.questions import CreateQuestion, DeleteQuestion
from app.domain.entities import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, PublicQuestion, User
from app.domain.errors import (
    ConflictError,
    ForbiddenError,
    InvalidError,
    NotFoundError,
    UnauthorizedError,
)

from .fakes import FakeCache, FakeClock, FakeHasher, FakeTokens, FakeUnitOfWork

POLICY = AttemptPolicy(cache_enabled=True, cache_ttl_seconds=60, submit_grace_seconds=5)
run = asyncio.run


class World:
    """Một kỳ thi mẫu: giáo viên, 4 câu hỏi (đáp án đúng là lựa chọn thứ hai), đề đã công bố, một sinh viên."""

    def __init__(self, *, published: bool = True, duration: int = 30, end_in: timedelta = timedelta(days=1)):
        self.uow, self.clock, self.cache = FakeUnitOfWork(), FakeClock(), FakeCache()
        self.teacher: User = run(self.uow.users.add(User("gv", "GV", ROLE_TEACHER, "h")))
        self.student: User = run(self.uow.users.add(User("sv", "SV", ROLE_STUDENT, "h")))
        self.questions = [
            run(CreateQuestion(self.uow).execute(
                self.teacher.id, f"Câu {i}?", [NewChoice("A"), NewChoice("B", True), NewChoice("C"), NewChoice("D")]))
            for i in range(4)
        ]
        now = self.clock.now()
        exam = run(CreateExam(self.uow).execute(
            self.teacher, "Đề", "", duration, now - timedelta(hours=1), now + end_in,
            [NewExamItem(q.id) for q in self.questions]))
        self.exam_id = exam.id
        if published:
            run(PublishExam(self.uow, self.cache, self.clock).execute(exam.id, self.teacher))

    def correct(self, i: int) -> int:
        return next(c.id for c in self.questions[i].choices if c.is_correct)

    def wrong(self, i: int) -> int:
        return next(c.id for c in self.questions[i].choices if not c.is_correct)

    def start(self, user: User | None = None):
        return run(StartAttempt(self.uow, self.cache, self.clock, POLICY).execute(self.exam_id, (user or self.student).id))

    def save(self, attempt_id: int, answers: list[AnswerChoice], user: User | None = None):
        return run(SaveAnswers(self.uow, self.clock, POLICY).execute(attempt_id, (user or self.student).id, answers))

    def submit(self, attempt_id: int):
        return run(SubmitAttempt(self.uow, self.clock).execute(attempt_id, self.student.id))


# ---------------------------------------------------------------- auth
def test_register_hashes_password_and_rejects_duplicate():
    uow = FakeUnitOfWork()
    user = run(RegisterStudent(uow, FakeHasher()).execute("nghi", "secret1", "Nghi"))
    assert user.role == ROLE_STUDENT and user.password_hash == "hashed:secret1"
    with pytest.raises(ConflictError):
        run(RegisterStudent(uow, FakeHasher()).execute("nghi", "other", "Nghi 2"))


def test_login_and_authenticate():
    uow = FakeUnitOfWork()
    run(RegisterStudent(uow, FakeHasher()).execute("nghi", "secret1", "Nghi"))
    login = Login(uow, FakeHasher(), FakeTokens())
    token, user = run(login.execute("nghi", "secret1"))
    assert run(Authenticate(uow, FakeTokens()).execute(token)).id == user.id
    with pytest.raises(UnauthorizedError):
        run(login.execute("nghi", "sai"))
    with pytest.raises(UnauthorizedError):
        run(login.execute("khong-co", "secret1"))
    with pytest.raises(UnauthorizedError):
        run(Authenticate(uow, FakeTokens()).execute("rac"))
    with pytest.raises(UnauthorizedError, match="không tồn tại"):
        run(Authenticate(uow, FakeTokens()).execute("token-999-student"))


# ---------------------------------------------------------------- câu hỏi và đề
def test_question_needs_exactly_one_correct():
    uow = FakeUnitOfWork()
    for choices in ([NewChoice("A"), NewChoice("B")], [NewChoice("A", True), NewChoice("B", True)]):
        with pytest.raises(InvalidError):
            run(CreateQuestion(uow).execute(1, "Câu sai?", choices))


def test_cannot_delete_question_used_in_exam():
    w = World()
    with pytest.raises(ConflictError):
        run(DeleteQuestion(w.uow).execute(w.questions[0].id))
    with pytest.raises(NotFoundError):
        run(DeleteQuestion(w.uow).execute(9999))


def test_create_exam_rejects_duplicate_or_unknown_questions():
    w = World()
    now = w.clock.now()
    create = CreateExam(w.uow)
    q = w.questions[0].id
    with pytest.raises(InvalidError, match="trùng"):
        run(create.execute(w.teacher, "Đề", "", 10, now, now + timedelta(hours=1), [NewExamItem(q), NewExamItem(q)]))
    with pytest.raises(InvalidError, match="không tồn tại"):
        run(create.execute(w.teacher, "Đề", "", 10, now, now + timedelta(hours=1), [NewExamItem(424242)]))


def test_publish_invalidates_cache_and_checks_owner():
    w = World(published=False)
    w.cache.set(w.exam_id, (), 60)
    other = run(w.uow.users.add(User("gv2", "GV2", ROLE_TEACHER, "h")))
    with pytest.raises(ForbiddenError):
        run(PublishExam(w.uow, w.cache, w.clock).execute(w.exam_id, other))
    exam = run(PublishExam(w.uow, w.cache, w.clock).execute(w.exam_id, w.teacher))
    assert exam.is_published and w.cache.get(w.exam_id) is None


def test_exam_detail_visible_to_owner_and_admin_only():
    w = World()
    admin = run(w.uow.users.add(User("ad", "AD", ROLE_ADMIN, "h")))
    other = run(w.uow.users.add(User("gv2", "GV2", ROLE_TEACHER, "h")))
    uc = GetExamDetail(w.uow)
    _, questions = run(uc.execute(w.exam_id, w.teacher))
    assert len(questions) == 4 and any(c.is_correct for c in questions[0].choices)
    run(uc.execute(w.exam_id, admin))
    with pytest.raises(ForbiddenError):
        run(uc.execute(w.exam_id, other))


# ---------------------------------------------------------------- làm bài
def test_start_is_idempotent_and_hides_correct_answers():
    w = World()
    first, created1 = w.start()
    second, created2 = w.start()
    assert (created1, created2) == (True, False)
    assert first.attempt.id == second.attempt.id
    assert all(isinstance(q, PublicQuestion) and not hasattr(q.choices[0], "is_correct") for q in first.questions)


def test_start_rejects_unpublished_and_outside_window():
    assert_raises = pytest.raises
    with assert_raises(NotFoundError):
        World(published=False).start()
    w = World()
    w.clock.advance(days=2)
    with assert_raises(ForbiddenError, match="đã kết thúc"):
        w.start()


def test_deadline_never_exceeds_exam_end():
    w = World(duration=300, end_in=timedelta(minutes=10))
    view, _ = w.start()
    assert view.attempt.deadline == w.clock.now() + timedelta(minutes=10)
    assert view.remaining_seconds == 600


def test_start_recovers_when_concurrent_request_wins_the_race():
    w = World()
    w.uow.attempts.race_for = (w.exam_id, w.student.id)
    view, created = w.start()
    assert created is False  # request thua cuộc đua trả về bài làm đã tạo bởi request kia
    assert view.attempt.user_id == w.student.id


def test_question_cache_used_when_enabled_only():
    w = World()
    attempt = w.start()[0].attempt
    run(GetAttempt(w.uow, w.cache, w.clock, POLICY).execute(attempt.id, w.student.id))
    assert w.cache.sets == 1  # lần start đã nạp cache, lần get dùng lại
    w2 = World()
    off = AttemptPolicy(cache_enabled=False, cache_ttl_seconds=60, submit_grace_seconds=5)
    run(StartAttempt(w2.uow, w2.cache, w2.clock, off).execute(w2.exam_id, w2.student.id))
    assert w2.cache.sets == 0


def test_save_answers_validates_ownership_and_pairs():
    w = World()
    attempt_id = w.start()[0].attempt.id
    with pytest.raises(InvalidError):
        w.save(attempt_id, [AnswerChoice(w.questions[0].id, w.correct(1))])  # đáp án của câu khác
    other = run(w.uow.users.add(User("sv2", "SV2", ROLE_STUDENT, "h")))
    with pytest.raises(NotFoundError):
        w.save(attempt_id, [], user=other)
    w.save(attempt_id, [AnswerChoice(w.questions[0].id, w.wrong(0))])
    w.save(attempt_id, [AnswerChoice(w.questions[0].id, w.correct(0))])  # đổi ý: chỉ giữ lựa chọn mới nhất
    assert run(w.uow.attempts.saved_answers(attempt_id)) == {w.questions[0].id: w.correct(0)}


def test_save_answers_blocked_after_deadline_plus_grace_and_after_submit():
    w = World()
    attempt_id = w.start()[0].attempt.id
    w.clock.advance(minutes=30, seconds=6)
    with pytest.raises(ConflictError, match="hết giờ"):
        w.save(attempt_id, [AnswerChoice(w.questions[0].id, w.correct(0))])
    w2 = World()
    a2 = w2.start()[0].attempt.id
    w2.submit(a2)
    with pytest.raises(ConflictError, match="đã nộp"):
        w2.save(a2, [])


def test_submit_grades_once_and_is_idempotent():
    w = World()
    attempt_id = w.start()[0].attempt.id
    w.save(attempt_id, [AnswerChoice(w.questions[0].id, w.correct(0)), AnswerChoice(w.questions[1].id, w.correct(1)),
                        AnswerChoice(w.questions[2].id, w.wrong(2))])
    first, was_first = w.submit(attempt_id)
    w.clock.advance(minutes=1)
    second, was_first_again = w.submit(attempt_id)
    assert (was_first, was_first_again) == (True, False)
    assert (first.correct, first.total, first.attempt.score) == (2, 4, 5.0)
    assert second.attempt.submitted_at == first.attempt.submitted_at and second.attempt.score == 5.0
    assert first.attempt.auto_submitted is False


def test_result_requires_submission():
    w = World()
    attempt_id = w.start()[0].attempt.id
    with pytest.raises(ConflictError):
        run(GetAttemptResult(w.uow, w.clock).execute(attempt_id, w.student.id))


def test_auto_submit_expired_attempts():
    w = World()
    attempt_id = w.start()[0].attempt.id
    w.save(attempt_id, [AnswerChoice(w.questions[0].id, w.correct(0))])
    assert run(AutoSubmitExpiredAttempts(w.uow, w.clock).execute()) == 0  # chưa hết giờ
    deadline = w.start()[0].attempt.deadline
    w.clock.advance(minutes=31)
    assert run(AutoSubmitExpiredAttempts(w.uow, w.clock).execute()) == 1
    done = run(GetAttemptResult(w.uow, w.clock).execute(attempt_id, w.student.id))
    assert done.attempt.auto_submitted is True and done.attempt.submitted_at == deadline
    assert done.attempt.score == 2.5  # 1/4 câu đúng
    assert run(AutoSubmitExpiredAttempts(w.uow, w.clock).execute()) == 0  # không thu lại lần hai
