from app.application.dto import NewChoice
from app.domain import rules
from app.domain.entities import Choice, Question
from app.domain.errors import ConflictError, InvalidError, NotFoundError
from app.domain.repositories import UnitOfWork


class CreateQuestion:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, owner_id: int, content: str, choices: list[NewChoice]) -> Question:
        if not rules.exactly_one_correct([c.is_correct for c in choices]):
            raise InvalidError("Câu hỏi phải có đúng 1 đáp án đúng")
        question = await self.uow.questions.add(
            Question(content, owner_id, [Choice(c.text, c.is_correct) for c in choices])
        )
        await self.uow.commit()
        return question


class SearchQuestions:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, text: str | None, skip: int, limit: int) -> tuple[int, list[Question]]:
        return await self.uow.questions.search(text, skip, limit)


class GetQuestion:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, question_id: int) -> Question:
        question = await self.uow.questions.get(question_id)
        if question is None:
            raise NotFoundError("Không tìm thấy câu hỏi")
        return question


class DeleteQuestion:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, question_id: int) -> None:
        if await self.uow.questions.get(question_id) is None:
            raise NotFoundError("Không tìm thấy câu hỏi")
        if await self.uow.questions.is_used_in_exam(question_id):
            raise ConflictError("Câu hỏi đang được dùng trong đề thi")
        await self.uow.questions.delete(question_id)
        await self.uow.commit()
