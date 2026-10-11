"""Cổng (port) cho các dịch vụ bên ngoài. Tầng infrastructure cài đặt, tầng application chỉ biết giao diện."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.domain.entities import PublicQuestion


class PasswordHasher(Protocol):
    async def hash(self, password: str) -> str: ...

    async def verify(self, password: str, stored: str | None) -> bool:
        """stored=None: vẫn băm thử một mật khẩu giả rồi trả False (chống dò tên đăng nhập qua thời gian phản hồi)."""
        ...


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    role: str


class TokenService(Protocol):
    def create(self, user_id: int, role: str) -> str: ...

    def decode(self, token: str) -> TokenPayload:
        """Ném UnauthorizedError nếu token sai hoặc hết hạn."""
        ...


class Clock(Protocol):
    def now(self) -> datetime:
        """UTC không kèm tzinfo."""
        ...


class ExamQuestionCache(Protocol):
    def get(self, exam_id: int) -> tuple[PublicQuestion, ...] | None: ...

    def set(self, exam_id: int, questions: tuple[PublicQuestion, ...], ttl: float) -> None: ...

    def invalidate(self, exam_id: int) -> None: ...
