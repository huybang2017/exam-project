from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain import rules
from app.domain.entities import PublicQuestion


class ChoiceIn(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool = False


class QuestionIn(BaseModel):
    content: str = Field(min_length=3)
    choices: list[ChoiceIn] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def exactly_one_correct(self):
        if not rules.exactly_one_correct([c.is_correct for c in self.choices]):
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

    @classmethod
    def from_entity(cls, q: PublicQuestion) -> "QuestionPublic":
        return cls(id=q.id, content=q.content, points=q.points,
                   choices=[ChoicePublic(id=c.id, text=c.text) for c in q.choices])
