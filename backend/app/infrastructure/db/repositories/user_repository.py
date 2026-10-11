from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import User
from app.domain.errors import ConflictError
from app.infrastructure.db.mappers import to_user
from app.infrastructure.db.orm_models import UserORM


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: int) -> User | None:
        orm = await self.session.get(UserORM, user_id)
        return to_user(orm) if orm else None

    async def get_by_username(self, username: str) -> User | None:
        orm = (await self.session.execute(select(UserORM).where(UserORM.username == username))).scalar_one_or_none()
        return to_user(orm) if orm else None

    async def add(self, user: User) -> User:
        orm = UserORM(username=user.username, full_name=user.full_name, role=user.role,
                      password_hash=user.password_hash)
        self.session.add(orm)
        try:
            await self.session.flush()
        except IntegrityError:
            raise ConflictError("Tên đăng nhập đã tồn tại")
        return to_user(orm)

    async def list(self, role: str | None, skip: int, limit: int) -> tuple[int, list[User]]:
        stmt = select(UserORM)
        if role:
            stmt = stmt.where(UserORM.role == role)
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self.session.execute(stmt.order_by(UserORM.id).offset(skip).limit(limit))).scalars().all()
        return total, [to_user(r) for r in rows]

    async def count(self) -> int:
        return (await self.session.execute(select(func.count()).select_from(UserORM))).scalar_one()
