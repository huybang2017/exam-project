"""Thực thể nghiệp vụ thuần Python: không biết gì về ORM, HTTP hay Pydantic."""
from dataclasses import dataclass, field
from datetime import datetime

ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"


@dataclass
class User:
    username: str
    full_name: str
    role: str
    password_hash: str
    id: int | None = None


@dataclass
class Choice:
    text: str
    is_correct: bool = False
    id: int | None = None


@dataclass
class Question:
    content: str
    owner_id: int
    choices: list[Choice] = field(default_factory=list)
    id: int | None = None


@dataclass
class ExamItem:
    question_id: int
    points: float = 1.0
    position: int = 0


@dataclass
class Exam:
    title: str
    description: str
    duration_minutes: int
    start_time: datetime
    end_time: datetime
    owner_id: int
    is_published: bool = False
    items: list[ExamItem] = field(default_factory=list)
    id: int | None = None


@dataclass
class Attempt:
    exam_id: int
    user_id: int
    started_at: datetime
    deadline: datetime
    submitted_at: datetime | None = None
    score: float | None = None
    auto_submitted: bool = False
    id: int | None = None

    @property
    def is_submitted(self) -> bool:
        return self.submitted_at is not None


# --- Giá trị chỉ đọc dùng cho truy vấn/kết quả -------------------------------------------------
@dataclass(frozen=True)
class PublicChoice:
    id: int
    text: str


@dataclass(frozen=True)
class PublicQuestion:
    """Câu hỏi gửi cho thí sinh: KHÔNG có is_correct."""

    id: int
    content: str
    points: float
    choices: tuple[PublicChoice, ...]


@dataclass(frozen=True)
class GradeInputs:
    earned_points: float
    correct_count: int
    total_points: float
    total_questions: int


@dataclass(frozen=True)
class ExamResultRow:
    user_id: int
    username: str
    full_name: str
    score: float | None
    submitted_at: datetime | None
    auto_submitted: bool
