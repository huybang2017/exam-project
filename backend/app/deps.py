import time
from collections import defaultdict, deque
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

DB = Annotated[AsyncSession, Depends(get_db)]


async def user_from_token(token: str, db: AsyncSession) -> User:
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ hoặc đã hết hạn",
                            headers={"WWW-Authenticate": "Bearer"})
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Người dùng không tồn tại")
    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DB) -> User:
    return await user_from_token(token, db)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    """Dependency factory: chỉ cho phép các vai trò được liệt kê."""

    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không có quyền thực hiện thao tác này")
        return user

    return checker


Teacher = Annotated[User, Depends(require_roles("teacher", "admin"))]
Admin = Annotated[User, Depends(require_roles("admin"))]
Student = Annotated[User, Depends(require_roles("student"))]


_login_hits: dict[str, deque[float]] = defaultdict(deque)


async def login_rate_limit(request: Request) -> None:
    """Giới hạn số lần đăng nhập theo IP (sliding window, in-memory)."""
    if not settings.rate_limit_enabled:
        return
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _login_hits[ip]
    while hits and hits[0] < now - settings.login_rate_window_seconds:
        hits.popleft()
    if len(hits) >= settings.login_rate_limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Đăng nhập quá nhiều lần, thử lại sau")
    hits.append(now)
