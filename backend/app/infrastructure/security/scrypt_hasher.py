import asyncio
import hashlib
import hmac
import os

_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


def _hash_sync(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${dk.hex()}"


def _verify_sync(password: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(dk.hex(), dk_hex)  # so sánh thời gian hằng số


class ScryptHasher:
    """Băm mật khẩu bằng scrypt. Tốn CPU nên chạy ở luồng riêng (hashlib.scrypt nhả GIL) để không chặn event loop."""

    def __init__(self) -> None:
        # Băm thử khi không có user để thời gian phản hồi không lộ username nào tồn tại.
        self._dummy_hash = _hash_sync("dummy-password")

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(_hash_sync, password)

    async def verify(self, password: str, stored: str | None) -> bool:
        if stored is None:
            await asyncio.to_thread(_verify_sync, password, self._dummy_hash)
            return False
        return await asyncio.to_thread(_verify_sync, password, stored)
