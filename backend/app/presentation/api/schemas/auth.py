from pydantic import BaseModel, ConfigDict, Field

from app.presentation.api.schemas.common import Role


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=6, max_length=100)
    full_name: str = Field(min_length=1, max_length=100)


class UserCreate(RegisterIn):
    role: Role = "student"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
