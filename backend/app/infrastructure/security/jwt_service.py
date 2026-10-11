from datetime import UTC, datetime, timedelta

import jwt

from app.domain.errors import UnauthorizedError
from app.domain.ports import TokenPayload


class JwtTokenService:
    def __init__(self, secret_key: str, algorithm: str, expire_minutes: int) -> None:
        self.secret_key, self.algorithm, self.expire_minutes = secret_key, algorithm, expire_minutes

    def create(self, user_id: int, role: str) -> str:
        exp = datetime.now(UTC) + timedelta(minutes=self.expire_minutes)
        return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, self.secret_key, algorithm=self.algorithm)

    def decode(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenPayload(int(payload["sub"]), payload.get("role", ""))
        except (jwt.PyJWTError, KeyError, ValueError):
            raise UnauthorizedError("Token không hợp lệ hoặc đã hết hạn")
