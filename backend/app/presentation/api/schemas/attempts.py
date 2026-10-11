from pydantic import BaseModel

from app.application.dto import AttemptResult, AttemptView
from app.presentation.api.schemas.common import UtcDT
from app.presentation.api.schemas.questions import QuestionPublic


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

    @classmethod
    def from_view(cls, v: AttemptView) -> "AttemptOut":
        a = v.attempt
        return cls(id=a.id, exam_id=a.exam_id, started_at=a.started_at, deadline=a.deadline,
                   remaining_seconds=v.remaining_seconds, submitted=a.is_submitted, score=a.score)


class AttemptDetail(AttemptOut):
    questions: list[QuestionPublic]
    saved_answers: dict[int, int]  # question_id -> choice_id

    @classmethod
    def from_view(cls, v: AttemptView) -> "AttemptDetail":
        base = AttemptOut.from_view(v).model_dump()
        return cls(**base, questions=[QuestionPublic.from_entity(q) for q in v.questions or ()],
                   saved_answers=v.saved_answers)


class ResultOut(BaseModel):
    attempt_id: int
    exam_id: int
    score: float
    correct: int
    total: int
    auto_submitted: bool
    submitted_at: UtcDT

    @classmethod
    def from_result(cls, r: AttemptResult) -> "ResultOut":
        a = r.attempt
        return cls(attempt_id=a.id, exam_id=a.exam_id, score=a.score, correct=r.correct, total=r.total,
                   auto_submitted=a.auto_submitted, submitted_at=a.submitted_at)
