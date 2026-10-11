from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import (
    ROLE_STUDENT,
    ROLE_TEACHER,
    Exam,
    PublicChoice,
    PublicQuestion,
    Question,
    User,
)
from app.infrastructure.db.mappers import to_exam, to_question
from app.infrastructure.db.orm_models import ChoiceORM, ExamORM, ExamQuestionORM, QuestionORM


class SqlAlchemyExamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, exam: Exam) -> Exam:
        orm = ExamORM(
            title=exam.title, description=exam.description, duration_minutes=exam.duration_minutes,
            start_time=exam.start_time, end_time=exam.end_time, owner_id=exam.owner_id,
            is_published=exam.is_published,
            items=[ExamQuestionORM(question_id=i.question_id, points=i.points, position=i.position) for i in exam.items],
        )
        self.session.add(orm)
        await self.session.flush()
        return to_exam(orm)

    async def get(self, exam_id: int) -> Exam | None:
        orm = (
            await self.session.execute(select(ExamORM).options(selectinload(ExamORM.items)).where(ExamORM.id == exam_id))
        ).scalar_one_or_none()
        return to_exam(orm) if orm else None

    async def list_for(self, user: User) -> list[Exam]:
        stmt = select(ExamORM).options(selectinload(ExamORM.items)).order_by(ExamORM.start_time.desc())
        if user.role == ROLE_STUDENT:
            stmt = stmt.where(ExamORM.is_published.is_(True))
        elif user.role == ROLE_TEACHER:
            stmt = stmt.where(ExamORM.owner_id == user.id)
        return [to_exam(o) for o in (await self.session.execute(stmt)).scalars().all()]

    async def save(self, exam: Exam) -> None:
        orm = await self.session.get(ExamORM, exam.id)
        orm.title, orm.description = exam.title, exam.description
        orm.duration_minutes = exam.duration_minutes
        orm.start_time, orm.end_time = exam.start_time, exam.end_time
        orm.is_published = exam.is_published
        await self.session.flush()

    async def questions_with_answers(self, exam_id: int) -> list[Question]:
        rows = (
            await self.session.execute(
                select(QuestionORM)
                .options(selectinload(QuestionORM.choices))
                .join(ExamQuestionORM, ExamQuestionORM.question_id == QuestionORM.id)
                .where(ExamQuestionORM.exam_id == exam_id)
                .order_by(ExamQuestionORM.position)
            )
        ).scalars().all()
        return [to_question(r) for r in rows]

    async def public_questions(self, exam_id: int) -> tuple[PublicQuestion, ...]:
        rows = (
            await self.session.execute(
                select(QuestionORM, ExamQuestionORM.points)
                .options(selectinload(QuestionORM.choices))
                .join(ExamQuestionORM, ExamQuestionORM.question_id == QuestionORM.id)
                .where(ExamQuestionORM.exam_id == exam_id)
                .order_by(ExamQuestionORM.position)
            )
        ).all()
        return tuple(
            PublicQuestion(q.id, q.content, points, tuple(PublicChoice(c.id, c.text) for c in q.choices))
            for q, points in rows
        )

    async def valid_choice_pairs(self, exam_id: int, choice_ids: list[int]) -> set[tuple[int, int]]:
        rows = (
            await self.session.execute(
                select(ChoiceORM.id, ChoiceORM.question_id)
                .join(ExamQuestionORM, ExamQuestionORM.question_id == ChoiceORM.question_id)
                .where(ExamQuestionORM.exam_id == exam_id, ChoiceORM.id.in_(choice_ids))
            )
        ).all()
        return {(cid, qid) for cid, qid in rows}
