from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import Question
from app.infrastructure.db.mappers import question_to_orm, to_question
from app.infrastructure.db.orm_models import ExamQuestionORM, QuestionORM


class SqlAlchemyQuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, question: Question) -> Question:
        orm = question_to_orm(question)
        self.session.add(orm)
        await self.session.flush()
        return to_question(orm)

    async def _load(self, question_id: int) -> QuestionORM | None:
        return (
            await self.session.execute(
                select(QuestionORM).options(selectinload(QuestionORM.choices)).where(QuestionORM.id == question_id)
            )
        ).scalar_one_or_none()

    async def get(self, question_id: int) -> Question | None:
        orm = await self._load(question_id)
        return to_question(orm) if orm else None

    async def search(self, text: str | None, skip: int, limit: int) -> tuple[int, list[Question]]:
        stmt = select(QuestionORM)
        if text:
            stmt = stmt.where(QuestionORM.content.ilike(f"%{text}%"))
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                stmt.options(selectinload(QuestionORM.choices)).order_by(QuestionORM.id.desc()).offset(skip).limit(limit)
            )
        ).scalars().all()
        return total, [to_question(r) for r in rows]

    async def delete(self, question_id: int) -> None:
        orm = await self._load(question_id)
        if orm is not None:
            await self.session.delete(orm)
            await self.session.flush()

    async def is_used_in_exam(self, question_id: int) -> bool:
        used = (
            await self.session.execute(
                select(func.count()).select_from(ExamQuestionORM).where(ExamQuestionORM.question_id == question_id)
            )
        ).scalar_one()
        return used > 0

    async def count_existing(self, question_ids: list[int]) -> int:
        if not question_ids:
            return 0
        return (
            await self.session.execute(
                select(func.count()).select_from(QuestionORM).where(QuestionORM.id.in_(question_ids))
            )
        ).scalar_one()
