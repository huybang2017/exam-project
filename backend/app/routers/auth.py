import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import DB, CurrentUser, login_rate_limit
from app.models import User
from app.schemas import RegisterIn, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# Băm thử khi không có user để thời gian phản hồi không lộ username nào tồn tại.
_DUMMY_HASH = hash_password("dummy-password")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, db: DB):
    """Sinh viên tự đăng ký. Giáo viên/Admin do Admin tạo qua /api/users."""
    # scrypt tốn CPU: chạy ở luồng riêng để không chặn event loop
    password_hash = await asyncio.to_thread(hash_password, data.password)
    user = User(username=data.username, full_name=data.full_name, role="student", password_hash=password_hash)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Tên đăng nhập đã tồn tại")
    return user


@router.post("/login", response_model=TokenOut, dependencies=[Depends(login_rate_limit)])
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    user = (await db.execute(select(User).where(User.username == form.username))).scalar_one_or_none()
    stored = user.password_hash if user else _DUMMY_HASH
    ok = await asyncio.to_thread(verify_password, form.password, stored)
    if user is None or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sai tên đăng nhập hoặc mật khẩu")
    return TokenOut(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
