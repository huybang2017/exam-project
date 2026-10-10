from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.deps import DB, Teacher
from app.models import Choice, ExamQuestion, Question
from app.schemas import Page, QuestionIn, QuestionOut

router = APIRouter(prefix="/api/questions", tags=["Question bank"])


@router.post("", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(data: QuestionIn, db: DB, user: Teacher):
    q = Question(content=data.content, owner_id=user.id,
                 choices=[Choice(text=c.text, is_correct=c.is_correct) for c in data.choices])
    db.add(q)
    await db.commit()
    return q


@router.get("", response_model=Page)
async def list_questions(
    db: DB,
    _: Teacher,
    q: Annotated[str | None, Query(description="Tìm theo nội dung")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    stmt = select(Question)
    if q:
        stmt = stmt.where(Question.content.ilike(f"%{q}%"))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await db.execute(stmt.options(selectinload(Question.choices)).order_by(Question.id.desc()).offset(skip).limit(limit))
    ).scalars().all()
    return Page(total=total, items=[QuestionOut.model_validate(r) for r in rows])


@router.get("/{question_id}", response_model=QuestionOut)
async def get_question(question_id: int, db: DB, _: Teacher):
    q = (
        await db.execute(select(Question).options(selectinload(Question.choices)).where(Question.id == question_id))
    ).scalar_one_or_none()
    if q is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy câu hỏi")
    return q


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(question_id: int, db: DB, _: Teacher):
    q = await db.get(Question, question_id)
    if q is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy câu hỏi")
    used = (await db.execute(select(func.count()).select_from(ExamQuestion).where(ExamQuestion.question_id == question_id))).scalar_one()
    if used:
        raise HTTPException(status.HTTP_409_CONFLICT, "Câu hỏi đang được dùng trong đề thi")
    await db.delete(q)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
