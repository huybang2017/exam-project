from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

IS_SQLITE = settings.database_url.startswith("sqlite")

if IS_SQLITE:
    engine = create_async_engine(settings.database_url)

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")  # đọc/ghi đồng thời tốt hơn
        cur.execute("PRAGMA busy_timeout=10000")  # chờ khoá thay vì báo lỗi ngay
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

else:
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,  # tự bỏ kết nối chết (vd. sau khi DB khởi động lại)
    )


SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency: mỗi request một AsyncSession, tự đóng khi xong."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from app import models  # noqa: F401  (đăng ký metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
