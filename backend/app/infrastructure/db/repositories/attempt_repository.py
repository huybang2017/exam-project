from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Attempt, ExamResultRow, GradeInputs
from app.domain.errors import DuplicateAttemptError
from app.infrastructure.db.mappers import to_attempt
from app.infrastructure.db.orm_models import (
    AttemptAnswerORM,
    AttemptORM,
    ChoiceORM,
    ExamQuestionORM,
    UserORM,
)


class SqlAlchemyAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, attempt: Attempt) -> Attempt:
        orm = AttemptORM(exam_id=attempt.exam_id, user_id=attempt.user_id, started_at=attempt.started_at,
                         deadline=attempt.deadline)
        self.session.add(orm)
        try:
            await self.session.flush()
        except IntegrityError:
            raise DuplicateAttemptError()
        return to_attempt(orm)

    async def get(self, attempt_id: int) -> Attempt | None:
        orm = await self.session.get(AttemptORM, attempt_id)
        return to_attempt(orm) if orm else None

    async def get_for_exam_user(self, exam_id: int, user_id: int) -> Attempt | None:
        orm = (
            await self.session.execute(
                select(AttemptORM).where(AttemptORM.exam_id == exam_id, AttemptORM.user_id == user_id)
            )
        ).scalar_one_or_none()
        return to_attempt(orm) if orm else None

    async def list_for_user(self, user_id: int) -> list[Attempt]:
        rows = (
            await self.session.execute(
                select(AttemptORM).where(AttemptORM.user_id == user_id).order_by(AttemptORM.id.desc())
            )
        ).scalars().all()
        return [to_attempt(r) for r in rows]

    async def save(self, attempt: Attempt) -> None:
        orm = await self.session.get(AttemptORM, attempt.id)
        orm.deadline, orm.submitted_at = attempt.deadline, attempt.submitted_at
        orm.score, orm.auto_submitted = attempt.score, attempt.auto_submitted
        await self.session.flush()

    async def saved_answers(self, attempt_id: int) -> dict[int, int]:
        rows = (
            await self.session.execute(select(AttemptAnswerORM).where(AttemptAnswerORM.attempt_id == attempt_id))
        ).scalars().all()
        return {r.question_id: r.choice_id for r in rows}

    async def upsert_answers(self, attempt_id: int, answers: dict[int, int]) -> None:
        current = {
            r.question_id: r
            for r in (
                await self.session.execute(select(AttemptAnswerORM).where(AttemptAnswerORM.attempt_id == attempt_id))
            ).scalars().all()
        }
        for question_id, choice_id in answers.items():
            if question_id in current:
                current[question_id].choice_id = choice_id
            else:
                self.session.add(AttemptAnswerORM(attempt_id=attempt_id, question_id=question_id, choice_id=choice_id))
        await self.session.flush()

    async def grade_inputs(self, attempt: Attempt) -> GradeInputs:
        """Hai truy vấn tổng hợp trong CSDL thay vì kéo toàn bộ đáp án về Python."""
        total_points, total_questions = (
            await self.session.execute(
                select(func.coalesce(func.sum(ExamQuestionORM.points), 0), func.count())
                .select_from(ExamQuestionORM)
                .where(ExamQuestionORM.exam_id == attempt.exam_id)
            )
        ).one()
        earned, correct = (
            await self.session.execute(
                select(func.coalesce(func.sum(ExamQuestionORM.points), 0), func.count())
                .select_from(AttemptAnswerORM)
                .join(ChoiceORM, ChoiceORM.id == AttemptAnswerORM.choice_id)
                .join(
                    ExamQuestionORM,
                    (ExamQuestionORM.question_id == AttemptAnswerORM.question_id)
                    & (ExamQuestionORM.exam_id == attempt.exam_id),
                )
                .where(AttemptAnswerORM.attempt_id == attempt.id, ChoiceORM.is_correct.is_(True))
            )
        ).one()
        return GradeInputs(float(earned), int(correct), float(total_points), int(total_questions))

    async def list_expired(self, now: datetime) -> list[Attempt]:
        rows = (
            await self.session.execute(
                select(AttemptORM).where(AttemptORM.submitted_at.is_(None), AttemptORM.deadline < now)
            )
        ).scalars().all()
        return [to_attempt(r) for r in rows]

    async def results_for_exam(self, exam_id: int) -> list[ExamResultRow]:
        rows = (
            await self.session.execute(
                select(AttemptORM, UserORM)
                .join(UserORM, UserORM.id == AttemptORM.user_id)
                .where(AttemptORM.exam_id == exam_id)
                .order_by(UserORM.username)
            )
        ).all()
        return [
            ExamResultRow(u.id, u.username, u.full_name, a.score, a.submitted_at, a.auto_submitted) for a, u in rows
        ]
