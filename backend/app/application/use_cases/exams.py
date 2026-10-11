from datetime import datetime

from app.application.dto import NewExamItem
from app.domain import rules
from app.domain.entities import Exam, ExamItem, ExamResultRow, Question, User
from app.domain.errors import InvalidError, NotFoundError
from app.domain.ports import Clock, ExamQuestionCache
from app.domain.repositories import UnitOfWork


async def load_owned_exam(uow: UnitOfWork, exam_id: int, user: User) -> Exam:
    exam = await uow.exams.get(exam_id)
    if exam is None:
        raise NotFoundError("Không tìm thấy đề thi")
    rules.ensure_exam_owner(exam, user)
    return exam


class CreateExam:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(
        self,
        owner: User,
        title: str,
        description: str,
        duration_minutes: int,
        start_time: datetime,
        end_time: datetime,
        items: list[NewExamItem],
    ) -> Exam:
        ids = [i.question_id for i in items]
        if len(set(ids)) != len(ids):
            raise InvalidError("Có câu hỏi bị trùng trong đề")
        if await self.uow.questions.count_existing(ids) != len(ids):
            raise InvalidError("Có question_id không tồn tại")
        exam = await self.uow.exams.add(
            Exam(
                title=title,
                description=description,
                duration_minutes=duration_minutes,
                start_time=start_time,
                end_time=end_time,
                owner_id=owner.id,
                items=[ExamItem(i.question_id, i.points, n) for n, i in enumerate(items)],
            )
        )
        await self.uow.commit()
        return exam


class ListExams:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, user: User) -> list[Exam]:
        return await self.uow.exams.list_for(user)


class GetExamDetail:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, exam_id: int, user: User) -> tuple[Exam, list[Question]]:
        exam = await load_owned_exam(self.uow, exam_id, user)
        return exam, await self.uow.exams.questions_with_answers(exam_id)


class PublishExam:
    def __init__(self, uow: UnitOfWork, cache: ExamQuestionCache, clock: Clock) -> None:
        self.uow, self.cache, self.clock = uow, cache, clock

    async def execute(self, exam_id: int, user: User) -> Exam:
        exam = await load_owned_exam(self.uow, exam_id, user)
        rules.ensure_can_publish(exam, self.clock.now())
        exam.is_published = True
        await self.uow.exams.save(exam)
        await self.uow.commit()
        self.cache.invalidate(exam_id)
        return exam


class ExamResults:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, exam_id: int, user: User) -> list[ExamResultRow]:
        await load_owned_exam(self.uow, exam_id, user)
        return await self.uow.attempts.results_for_exam(exam_id)
