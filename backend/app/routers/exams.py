import csv
import io
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.cache import exam_cache
from app.deps import DB, CurrentUser, Teacher
from app.models import Attempt, Exam, ExamQuestion, Question, User, utcnow
from app.schemas import ExamDetail, ExamIn, ExamOut, ExamResultRow, QuestionOut

router = APIRouter(prefix="/api/exams", tags=["Exams"])


def _exam_out(exam: Exam) -> ExamOut:
    return ExamOut(id=exam.id, title=exam.title, description=exam.description,
                   duration_minutes=exam.duration_minutes, start_time=exam.start_time,
                   end_time=exam.end_time, is_published=exam.is_published,
                   question_count=len(exam.items))


async def _load_exam(db, exam_id: int) -> Exam:
    exam = (
        await db.execute(select(Exam).options(selectinload(Exam.items)).where(Exam.id == exam_id))
    ).scalar_one_or_none()
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy đề thi")
    return exam


def _check_owner(exam: Exam, user: User) -> None:
    if user.role != "admin" and exam.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Đề thi này thuộc giáo viên khác")


@router.post("", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
async def create_exam(data: ExamIn, db: DB, user: Teacher):
    ids = [i.question_id for i in data.items]
    if len(set(ids)) != len(ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Có câu hỏi bị trùng trong đề")
    found = (await db.execute(select(func.count()).select_from(Question).where(Question.id.in_(ids)))).scalar_one()
    if found != len(ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Có question_id không tồn tại")
    exam = Exam(title=data.title, description=data.description, duration_minutes=data.duration_minutes,
                start_time=data.start_time, end_time=data.end_time, owner_id=user.id,
                items=[ExamQuestion(question_id=i.question_id, points=i.points, position=n)
                       for n, i in enumerate(data.items)])
    db.add(exam)
    await db.commit()
    return _exam_out(exam)


@router.get("", response_model=list[ExamOut])
async def list_exams(db: DB, user: CurrentUser):
    """Thí sinh: chỉ thấy đề đã công bố. Giáo viên: đề của mình. Admin: tất cả."""
    stmt = select(Exam).options(selectinload(Exam.items)).order_by(Exam.start_time.desc())
    if user.role == "student":
        stmt = stmt.where(Exam.is_published.is_(True))
    elif user.role == "teacher":
        stmt = stmt.where(Exam.owner_id == user.id)
    return [_exam_out(e) for e in (await db.execute(stmt)).scalars().all()]


@router.get("/{exam_id}", response_model=ExamDetail)
async def get_exam(exam_id: int, db: DB, user: Teacher):
    exam = await _load_exam(db, exam_id)
    _check_owner(exam, user)
    qs = (
        await db.execute(
            select(Question).options(selectinload(Question.choices))
            .join(ExamQuestion, ExamQuestion.question_id == Question.id)
            .where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.position)
        )
    ).scalars().all()
    return ExamDetail(**_exam_out(exam).model_dump(), questions=[QuestionOut.model_validate(q) for q in qs])


@router.post("/{exam_id}/publish", response_model=ExamOut)
async def publish_exam(exam_id: int, db: DB, user: Teacher):
    exam = await _load_exam(db, exam_id)
    _check_owner(exam, user)
    if exam.end_time <= utcnow():
        raise HTTPException(status.HTTP_409_CONFLICT, "Đề đã quá thời gian kết thúc")
    exam.is_published = True
    await db.commit()
    exam_cache.invalidate(exam_id)
    return _exam_out(exam)


@router.get("/{exam_id}/results", response_model=list[ExamResultRow])
async def exam_results(exam_id: int, db: DB, user: Teacher):
    exam = await _load_exam(db, exam_id)
    _check_owner(exam, user)
    rows = (
        await db.execute(
            select(Attempt, User).join(User, User.id == Attempt.user_id)
            .where(Attempt.exam_id == exam_id).order_by(User.username)
        )
    ).all()
    return [ExamResultRow(user_id=u.id, username=u.username, full_name=u.full_name, score=a.score,
                          submitted_at=a.submitted_at, auto_submitted=a.auto_submitted) for a, u in rows]


@router.get("/{exam_id}/results.csv")
async def export_results_csv(exam_id: int, db: DB, user: Teacher):
    """Xuất bảng điểm CSV bằng StreamingResponse (không giữ cả file trong RAM)."""
    exam = await _load_exam(db, exam_id)
    _check_owner(exam, user)
    rows = await exam_results(exam_id, db, user)

    def generate() -> Iterator[str]:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["username", "full_name", "score", "submitted_at", "auto_submitted"])
        yield "﻿" + buf.getvalue()  # BOM để Excel đọc đúng tiếng Việt
        for r in rows:
            buf.seek(0)
            buf.truncate()
            w.writerow([r.username, r.full_name, r.score, r.submitted_at, r.auto_submitted])
            yield buf.getvalue()

    return StreamingResponse(
        generate(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="exam_{exam_id}_results.csv"'},
    )
