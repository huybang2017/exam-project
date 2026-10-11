from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,  # tự bỏ kết nối chết (vd. sau khi DB khởi động lại)
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Tạo bảng nếu chưa có (đồ án chưa dùng migration)."""
    from app.infrastructure.db import orm_models  # noqa: F401  (đăng ký metadata)
    from app.infrastructure.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
