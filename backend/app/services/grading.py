"""Chấm điểm và nộp bài - dùng chung cho API nộp bài, WebSocket và tác vụ nền tự thu bài."""
import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Attempt, AttemptAnswer, Choice, ExamQuestion, utcnow

log = logging.getLogger("exam.grading")


async def grade_attempt(db: AsyncSession, attempt: Attempt) -> tuple[float, int, int]:
    """Trả về (điểm thang 10, số câu đúng, tổng số câu) bằng 2 truy vấn tổng hợp."""
    total_points = (
        await db.execute(select(func.coalesce(func.sum(ExamQuestion.points), 0)).where(ExamQuestion.exam_id == attempt.exam_id))
    ).scalar_one()
    total_q = (
        await db.execute(select(func.count()).select_from(ExamQuestion).where(ExamQuestion.exam_id == attempt.exam_id))
    ).scalar_one()

    row = (
        await db.execute(
            select(func.coalesce(func.sum(ExamQuestion.points), 0), func.count())
            .select_from(AttemptAnswer)
            .join(Choice, Choice.id == AttemptAnswer.choice_id)
            .join(
                ExamQuestion,
                (ExamQuestion.question_id == AttemptAnswer.question_id) & (ExamQuestion.exam_id == attempt.exam_id),
            )
            .where(AttemptAnswer.attempt_id == attempt.id, Choice.is_correct.is_(True))
        )
    ).one()
    earned, correct = float(row[0]), int(row[1])
    score = round(earned / float(total_points) * 10, 2) if total_points else 0.0
    return score, correct, int(total_q)


async def submit_attempt(db: AsyncSession, attempt: Attempt, *, auto: bool = False, at: datetime | None = None) -> Attempt:
    """Nộp bài một lần duy nhất (idempotent): nếu đã nộp thì giữ nguyên kết quả."""
    if attempt.submitted_at is not None:
        return attempt
    score, _, _ = await grade_attempt(db, attempt)
    attempt.score = score
    attempt.submitted_at = at or min(utcnow(), attempt.deadline)
    attempt.auto_submitted = auto
    await db.commit()
    return attempt


async def auto_submit_expired(db: AsyncSession) -> int:
    """Thu bài tất cả bài làm đã quá hạn mà chưa nộp. Trả về số bài đã thu."""
    now = utcnow()
    expired = (
        await db.execute(select(Attempt).where(Attempt.submitted_at.is_(None), Attempt.deadline < now))
    ).scalars().all()
    for a in expired:
        await submit_attempt(db, a, auto=True, at=a.deadline)
    if expired:
        log.info("Tự động thu %d bài quá hạn", len(expired))
    return len(expired)
