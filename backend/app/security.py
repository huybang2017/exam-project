import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings

_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(dk.hex(), dk_hex)


def create_access_token(user_id: int, role: str) -> str:
    exp = datetime.now(UTC) + timedelta(minutes=settings.token_expire_minutes)
    payload = {"sub": str(user_id), "role": role, "exp": exp}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Ném jwt.PyJWTError nếu token sai hoặc hết hạn."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
