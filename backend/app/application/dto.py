"""Dữ liệu vào/ra của use case (dataclass thuần)."""
from dataclasses import dataclass, field

from app.domain.entities import Attempt, PublicQuestion


@dataclass(frozen=True)
class AttemptPolicy:
    cache_enabled: bool
    cache_ttl_seconds: int
    submit_grace_seconds: int


@dataclass(frozen=True)
class NewChoice:
    text: str
    is_correct: bool = False


@dataclass(frozen=True)
class NewExamItem:
    question_id: int
    points: float = 1.0


@dataclass(frozen=True)
class AnswerChoice:
    question_id: int
    choice_id: int


@dataclass
class AttemptView:
    attempt: Attempt
    remaining_seconds: int
    questions: tuple[PublicQuestion, ...] | None = None
    saved_answers: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class AttemptResult:
    attempt: Attempt
    correct: int
    total: int
