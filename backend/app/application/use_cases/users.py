from app.domain.entities import User
from app.domain.ports import PasswordHasher
from app.domain.repositories import UnitOfWork


class ListUsers:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def execute(self, role: str | None, skip: int, limit: int) -> tuple[int, list[User]]:
        return await self.uow.users.list(role, skip, limit)


class CreateUser:
    """Admin tạo tài khoản với vai trò bất kỳ."""

    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher) -> None:
        self.uow, self.hasher = uow, hasher

    async def execute(self, username: str, password: str, full_name: str, role: str) -> User:
        password_hash = await self.hasher.hash(password)
        user = await self.uow.users.add(User(username, full_name, role, password_hash))
        await self.uow.commit()
        return user
