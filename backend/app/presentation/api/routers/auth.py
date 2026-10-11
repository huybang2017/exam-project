from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.presentation.api.dependencies import CurrentUser, LoginDep, RegisterStudentDep, login_rate_limit
from app.presentation.api.schemas.auth import RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, use_case: RegisterStudentDep):
    """Sinh viên tự đăng ký. Giáo viên/Admin do Admin tạo qua /api/users."""
    return UserOut.model_validate(await use_case.execute(data.username, data.password, data.full_name))


@router.post("/login", response_model=TokenOut, dependencies=[Depends(login_rate_limit)])
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], use_case: LoginDep):
    token, user = await use_case.execute(form.username, form.password)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return UserOut.model_validate(user)
