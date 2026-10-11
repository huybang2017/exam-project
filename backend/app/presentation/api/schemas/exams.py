from pydantic import BaseModel, Field, model_validator

from app.domain.entities import Exam
from app.domain.entities import ExamResultRow as ExamResultRowEntity
from app.presentation.api.schemas.common import UtcDT
from app.presentation.api.schemas.questions import QuestionOut


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

    @classmethod
    def from_entity(cls, e: Exam) -> "ExamOut":
        return cls(id=e.id, title=e.title, description=e.description, duration_minutes=e.duration_minutes,
                   start_time=e.start_time, end_time=e.end_time, is_published=e.is_published,
                   question_count=len(e.items))


class ExamDetail(ExamOut):
    questions: list[QuestionOut]


class ExamResultRow(BaseModel):
    user_id: int
    username: str
    full_name: str
    score: float | None
    submitted_at: UtcDT | None
    auto_submitted: bool

    @classmethod
    def from_entity(cls, r: ExamResultRowEntity) -> "ExamResultRow":
        return cls(user_id=r.user_id, username=r.username, full_name=r.full_name, score=r.score,
                   submitted_at=r.submitted_at, auto_submitted=r.auto_submitted)
