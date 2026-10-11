from typing import Annotated

from fastapi import APIRouter, Query, status

from app.presentation.api.dependencies import Admin, CreateUserDep, ListUsersDep
from app.presentation.api.schemas.auth import UserCreate, UserOut
from app.presentation.api.schemas.common import Page, Role

router = APIRouter(prefix="/api/users", tags=["Users (Admin)"])


@router.get("", response_model=Page)
async def list_users(
    use_case: ListUsersDep,
    _: Admin,
    role: Role | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total, users = await use_case.execute(role, skip, limit)
    return Page(total=total, items=[UserOut.model_validate(u) for u in users])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, use_case: CreateUserDep, _: Admin):
    return UserOut.model_validate(await use_case.execute(data.username, data.password, data.full_name, data.role))
