from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.application.dto import NewChoice
from app.presentation.api.dependencies import (
    CreateQuestionDep,
    DeleteQuestionDep,
    GetQuestionDep,
    SearchQuestionsDep,
    Teacher,
)
from app.presentation.api.schemas.common import Page
from app.presentation.api.schemas.questions import QuestionIn, QuestionOut

router = APIRouter(prefix="/api/questions", tags=["Question bank"])


@router.post("", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(data: QuestionIn, use_case: CreateQuestionDep, user: Teacher):
    question = await use_case.execute(user.id, data.content, [NewChoice(c.text, c.is_correct) for c in data.choices])
    return QuestionOut.model_validate(question)


@router.get("", response_model=Page)
async def list_questions(
    use_case: SearchQuestionsDep,
    _: Teacher,
    q: Annotated[str | None, Query(description="Tìm theo nội dung")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    total, questions = await use_case.execute(q, skip, limit)
    return Page(total=total, items=[QuestionOut.model_validate(x) for x in questions])


@router.get("/{question_id}", response_model=QuestionOut)
async def get_question(question_id: int, use_case: GetQuestionDep, _: Teacher):
    return QuestionOut.model_validate(await use_case.execute(question_id))


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(question_id: int, use_case: DeleteQuestionDep, _: Teacher):
    await use_case.execute(question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
