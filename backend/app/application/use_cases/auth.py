from app.domain.entities import ROLE_STUDENT, User
from app.domain.errors import UnauthorizedError
from app.domain.ports import PasswordHasher, TokenService
from app.domain.repositories import UnitOfWork


class RegisterStudent:
    """Sinh viên tự đăng ký. Giáo viên/Admin do Admin tạo (CreateUser)."""

    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher) -> None:
        self.uow, self.hasher = uow, hasher

    async def execute(self, username: str, password: str, full_name: str) -> User:
        password_hash = await self.hasher.hash(password)
        user = await self.uow.users.add(User(username, full_name, ROLE_STUDENT, password_hash))
        await self.uow.commit()
        return user


class Login:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher, tokens: TokenService) -> None:
        self.uow, self.hasher, self.tokens = uow, hasher, tokens

    async def execute(self, username: str, password: str) -> tuple[str, User]:
        user = await self.uow.users.get_by_username(username)
        ok = await self.hasher.verify(password, user.password_hash if user else None)
        if user is None or not ok:
            raise UnauthorizedError("Sai tên đăng nhập hoặc mật khẩu")
        return self.tokens.create(user.id, user.role), user


class Authenticate:
    """Từ token trả về người dùng hiện tại. Vai trò luôn đọc lại từ CSDL, không tin token."""

    def __init__(self, uow: UnitOfWork, tokens: TokenService) -> None:
        self.uow, self.tokens = uow, tokens

    async def execute(self, token: str) -> User:
        payload = self.tokens.decode(token)
        user = await self.uow.users.get(payload.user_id)
        if user is None:
            raise UnauthorizedError("Người dùng không tồn tại")
        return user
