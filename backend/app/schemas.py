from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer, model_validator

Role = Literal["admin", "teacher", "student"]


def _to_naive_utc(v: datetime) -> datetime:
    if v.tzinfo is not None:
        v = v.astimezone(UTC).replace(tzinfo=None)
    return v


# Nhận datetime bất kỳ -> lưu UTC; trả ra luôn có hậu tố Z
UtcDT = Annotated[
    datetime,
    AfterValidator(_to_naive_utc),
    PlainSerializer(lambda v: v.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"), return_type=str),
]


# ---------- Auth / User ----------
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


# ---------- Question ----------
class ChoiceIn(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool = False


class QuestionIn(BaseModel):
    content: str = Field(min_length=3)
    choices: list[ChoiceIn] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def exactly_one_correct(self):
        if sum(c.is_correct for c in self.choices) != 1:
            raise ValueError("Câu hỏi phải có đúng 1 đáp án đúng")
        return self


class ChoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    is_correct: bool


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content: str
    choices: list[ChoiceOut]


class ChoicePublic(BaseModel):
    id: int
    text: str


class QuestionPublic(BaseModel):
    """Phiên bản gửi cho thí sinh - KHÔNG chứa is_correct."""

    id: int
    content: str
    points: float
    choices: list[ChoicePublic]


# ---------- Exam ----------
class ExamItemIn(BaseModel):
    question_id: int
    points: float = Field(default=1.0, gt=0, le=100)


class ExamIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    duration_minutes: int = Field(ge=1, le=300)
    start_time: UtcDT
    end_time: UtcDT
    items: list[ExamItemIn] = Field(min_length=1)

    @model_validator(mode="after")
    def check_window(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time phải sau start_time")
        return self


class ExamOut(BaseModel):
    id: int
    title: str
    description: str
    duration_minutes: int
    start_time: UtcDT
    end_time: UtcDT
    is_published: bool
    question_count: int


class ExamDetail(ExamOut):
    questions: list[QuestionOut]


# ---------- Attempt ----------
class AnswerIn(BaseModel):
    question_id: int
    choice_id: int


class AnswersIn(BaseModel):
    answers: list[AnswerIn]


class AttemptOut(BaseModel):
    id: int
    exam_id: int
    started_at: UtcDT
    deadline: UtcDT
    remaining_seconds: int
    submitted: bool
    score: float | None = None


class AttemptDetail(AttemptOut):
    questions: list[QuestionPublic]
    saved_answers: dict[int, int]  # question_id -> choice_id


class ResultOut(BaseModel):
    attempt_id: int
    exam_id: int
    score: float
    correct: int
    total: int
    auto_submitted: bool
    submitted_at: UtcDT


class ExamResultRow(BaseModel):
    user_id: int
    username: str
    full_name: str
    score: float | None
    submitted_at: UtcDT | None
    auto_submitted: bool


class Page(BaseModel):
    total: int
    items: list
