import logging
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.cache import exam_cache
from app.config import settings
from app.deps import DB, CurrentUser, Student
from app.models import Attempt, AttemptAnswer, Choice, Exam, ExamQuestion, Question, utcnow
from app.schemas import AnswersIn, AttemptDetail, AttemptOut, QuestionPublic, ResultOut
from app.services.grading import grade_attempt, submit_attempt

log = logging.getLogger("exam.notify")
router = APIRouter(tags=["Attempts (làm bài thi)"])


async def exam_questions_public(db, exam_id: int) -> list[dict]:
    """Danh sách câu hỏi gửi cho thí sinh (không có đáp án đúng). Đề đã công bố là bất biến nên cache an toàn."""
    if settings.cache_enabled:
        cached = exam_cache.get(exam_id)
        if cached is not None:
            return cached
    rows = (
        await db.execute(
            select(Question, ExamQuestion.points)
            .options(selectinload(Question.choices))
            .join(ExamQuestion, ExamQuestion.question_id == Question.id)
            .where(ExamQuestion.exam_id == exam_id)
            .order_by(ExamQuestion.position)
        )
    ).all()
    data = [
        QuestionPublic(id=q.id, content=q.content, points=p,
                       choices=[{"id": c.id, "text": c.text} for c in q.choices]).model_dump()
        for q, p in rows
    ]
    if settings.cache_enabled:
        exam_cache.set(exam_id, data, settings.cache_ttl_seconds)
    return data


def _remaining(a: Attempt) -> int:
    if a.submitted_at is not None:
        return 0
    return max(0, int((a.deadline - utcnow()).total_seconds()))


def _attempt_out(a: Attempt) -> AttemptOut:
    return AttemptOut(id=a.id, exam_id=a.exam_id, started_at=a.started_at, deadline=a.deadline,
                      remaining_seconds=_remaining(a), submitted=a.submitted_at is not None, score=a.score)


async def _attempt_detail(db, a: Attempt) -> AttemptDetail:
    answers = (await db.execute(select(AttemptAnswer).where(AttemptAnswer.attempt_id == a.id))).scalars().all()
    return AttemptDetail(**_attempt_out(a).model_dump(),
                         questions=await exam_questions_public(db, a.exam_id),
                         saved_answers={x.question_id: x.choice_id for x in answers})


async def get_own_attempt(db, attempt_id: int, user) -> Attempt:
    a = await db.get(Attempt, attempt_id)
    if a is None or a.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy bài làm")
    return a


@router.post("/api/exams/{exam_id}/attempts", response_model=AttemptDetail, tags=["Attempts (làm bài thi)"])
async def start_attempt(exam_id: int, response: Response, db: DB, user: Student):
    """Bắt đầu làm bài. Gọi lại nhiều lần vẫn trả về cùng một bài làm (idempotent) - hỗ trợ F5/vào lại khi rớt mạng."""
    exam = await db.get(Exam, exam_id)
    if exam is None or not exam.is_published:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy đề thi")
    now = utcnow()

    existing = (
        await db.execute(select(Attempt).where(Attempt.exam_id == exam_id, Attempt.user_id == user.id))
    ).scalar_one_or_none()
    if existing is not None:
        return await _attempt_detail(db, existing)

    if now < exam.start_time:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chưa đến giờ thi")
    if now > exam.end_time:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Kỳ thi đã kết thúc")

    deadline = min(now + timedelta(minutes=exam.duration_minutes), exam.end_time)
    attempt = Attempt(exam_id=exam_id, user_id=user.id, started_at=now, deadline=deadline)
    db.add(attempt)
    try:
        await db.commit()
        response.status_code = status.HTTP_201_CREATED
    except IntegrityError:  # hai request "bắt đầu" đến cùng lúc
        await db.rollback()
        attempt = (
            await db.execute(select(Attempt).where(Attempt.exam_id == exam_id, Attempt.user_id == user.id))
        ).scalar_one()
    return await _attempt_detail(db, attempt)


@router.get("/api/attempts", response_model=list[AttemptOut])
async def my_attempts(db: DB, user: Student):
    rows = (await db.execute(select(Attempt).where(Attempt.user_id == user.id).order_by(Attempt.id.desc()))).scalars().all()
    return [_attempt_out(a) for a in rows]


@router.get("/api/attempts/{attempt_id}", response_model=AttemptDetail)
async def get_attempt(attempt_id: int, db: DB, user: Student):
    return await _attempt_detail(db, await get_own_attempt(db, attempt_id, user))


@router.put("/api/attempts/{attempt_id}/answers", response_model=AttemptOut)
async def save_answers(attempt_id: int, data: AnswersIn, db: DB, user: Student):
    """Tự động lưu đáp án (autosave). Mỗi câu chỉ giữ lựa chọn mới nhất."""
    a = await get_own_attempt(db, attempt_id, user)
    if a.submitted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bài đã nộp, không thể sửa đáp án")
    if utcnow() > a.deadline + timedelta(seconds=settings.submit_grace_seconds):
        raise HTTPException(status.HTTP_409_CONFLICT, "Đã hết giờ làm bài")

    if data.answers:
        choice_ids = [x.choice_id for x in data.answers]
        valid = {
            (cid, qid)
            for cid, qid in (
                await db.execute(
                    select(Choice.id, Choice.question_id)
                    .join(ExamQuestion, ExamQuestion.question_id == Choice.question_id)
                    .where(ExamQuestion.exam_id == a.exam_id, Choice.id.in_(choice_ids))
                )
            ).all()
        }
        for x in data.answers:
            if (x.choice_id, x.question_id) not in valid:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    f"Đáp án {x.choice_id} không thuộc câu {x.question_id} của đề này")
        current = {
            r.question_id: r
            for r in (await db.execute(select(AttemptAnswer).where(AttemptAnswer.attempt_id == a.id))).scalars().all()
        }
        for x in data.answers:
            if x.question_id in current:
                current[x.question_id].choice_id = x.choice_id
            else:
                db.add(AttemptAnswer(attempt_id=a.id, question_id=x.question_id, choice_id=x.choice_id))
        await db.commit()
    return _attempt_out(a)


def notify_result(username: str, score: float) -> None:
    """Tác vụ nền: giả lập gửi email kết quả (thực tế: SMTP/queue)."""
    log.info("Đã gửi email kết quả tới %s: %.2f điểm", username, score)


@router.post("/api/attempts/{attempt_id}/submit", response_model=ResultOut)
async def submit(attempt_id: int, background: BackgroundTasks, db: DB, user: Student):
    a = await get_own_attempt(db, attempt_id, user)
    first_time = a.submitted_at is None
    await submit_attempt(db, a)
    if first_time:
        background.add_task(notify_result, user.username, a.score)
    return await _result(db, a)


async def _result(db, a: Attempt) -> ResultOut:
    _, correct, total = await grade_attempt(db, a)
    return ResultOut(attempt_id=a.id, exam_id=a.exam_id, score=a.score, correct=correct, total=total,
                     auto_submitted=a.auto_submitted, submitted_at=a.submitted_at)


@router.get("/api/attempts/{attempt_id}/result", response_model=ResultOut)
async def attempt_result(attempt_id: int, db: DB, user: CurrentUser):
    a = await get_own_attempt(db, attempt_id, user)
    if a.submitted_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bài chưa được nộp")
    return await _result(db, a)
