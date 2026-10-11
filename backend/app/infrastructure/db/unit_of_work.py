from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.repositories.attempt_repository import SqlAlchemyAttemptRepository
from app.infrastructure.db.repositories.exam_repository import SqlAlchemyExamRepository
from app.infrastructure.db.repositories.question_repository import SqlAlchemyQuestionRepository
from app.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository


class SqlAlchemyUnitOfWork:
    """Một phiên và một giao dịch cho một use case. Thoát khối `async with` mà chưa commit thì tự rollback."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self.session)
        self.questions = SqlAlchemyQuestionRepository(self.session)
        self.exams = SqlAlchemyExamRepository(self.session)
        self.attempts = SqlAlchemyAttemptRepository(self.session)
        return self

    async def __aexit__(self, *exc) -> None:
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
