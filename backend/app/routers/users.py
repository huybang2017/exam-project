import asyncio
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.deps import DB, Admin
from app.models import User
from app.schemas import Page, Role, UserCreate, UserOut
from app.security import hash_password

router = APIRouter(prefix="/api/users", tags=["Users (Admin)"])


@router.get("", response_model=Page)
async def list_users(
    db: DB,
    _: Admin,
    role: Role | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.order_by(User.id).offset(skip).limit(limit))).scalars().all()
    return Page(total=total, items=[UserOut.model_validate(u) for u in rows])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: DB, _: Admin):
    password_hash = await asyncio.to_thread(hash_password, data.password)
    user = User(username=data.username, full_name=data.full_name, role=data.role, password_hash=password_hash)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Tên đăng nhập đã tồn tại")
    return user
