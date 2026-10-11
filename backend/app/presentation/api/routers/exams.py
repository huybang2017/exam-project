import csv
import io
from collections.abc import Iterator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.application.dto import NewExamItem
from app.presentation.api.dependencies import (
    CreateExamDep,
    CurrentUser,
    ExamResultsDep,
    GetExamDetailDep,
    ListExamsDep,
    PublishExamDep,
    Teacher,
)
from app.presentation.api.schemas.exams import ExamDetail, ExamIn, ExamOut, ExamResultRow
from app.presentation.api.schemas.questions import QuestionOut

router = APIRouter(prefix="/api/exams", tags=["Exams"])


@router.post("", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
async def create_exam(data: ExamIn, use_case: CreateExamDep, user: Teacher):
    exam = await use_case.execute(
        user, data.title, data.description, data.duration_minutes, data.start_time, data.end_time,
        [NewExamItem(i.question_id, i.points) for i in data.items],
    )
    return ExamOut.from_entity(exam)


@router.get("", response_model=list[ExamOut])
async def list_exams(use_case: ListExamsDep, user: CurrentUser):
    """Thí sinh: chỉ thấy đề đã công bố. Giáo viên: đề của mình. Admin: tất cả."""
    return [ExamOut.from_entity(e) for e in await use_case.execute(user)]


@router.get("/{exam_id}", response_model=ExamDetail)
async def get_exam(exam_id: int, use_case: GetExamDetailDep, user: Teacher):
    exam, questions = await use_case.execute(exam_id, user)
    return ExamDetail(**ExamOut.from_entity(exam).model_dump(),
                      questions=[QuestionOut.model_validate(q) for q in questions])


@router.post("/{exam_id}/publish", response_model=ExamOut)
async def publish_exam(exam_id: int, use_case: PublishExamDep, user: Teacher):
    return ExamOut.from_entity(await use_case.execute(exam_id, user))


@router.get("/{exam_id}/results", response_model=list[ExamResultRow])
async def exam_results(exam_id: int, use_case: ExamResultsDep, user: Teacher):
    return [ExamResultRow.from_entity(r) for r in await use_case.execute(exam_id, user)]


@router.get("/{exam_id}/results.csv")
async def export_results_csv(exam_id: int, use_case: ExamResultsDep, user: Teacher):
    """Xuất bảng điểm CSV bằng StreamingResponse (không giữ cả file trong RAM)."""
    rows = await use_case.execute(exam_id, user)

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
