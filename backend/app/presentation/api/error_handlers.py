"""Ánh xạ lỗi nghiệp vụ -> mã HTTP ở một chỗ duy nhất (router không tự chọn mã lỗi)."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    InvalidError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
)

# Thứ tự quan trọng: lớp con (vd. DuplicateAttemptError là ConflictError) khớp theo isinstance.
_STATUS_BY_ERROR: list[tuple[type[DomainError], int]] = [
    (NotFoundError, 404),
    (UnauthorizedError, 401),
    (ForbiddenError, 403),
    (ConflictError, 409),
    (InvalidError, 422),
    (TooManyRequestsError, 429),
]


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    code = next((c for t, c in _STATUS_BY_ERROR if isinstance(exc, t)), 400)
    headers = {"WWW-Authenticate": "Bearer"} if code == 401 else None
    return JSONResponse({"detail": exc.message}, status_code=code, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
