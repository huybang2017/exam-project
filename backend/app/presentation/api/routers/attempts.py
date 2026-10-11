import logging

from fastapi import APIRouter, BackgroundTasks, Response, status

from app.application.dto import AnswerChoice
from app.presentation.api.dependencies import (
    CurrentUser,
    GetAttemptDep,
    GetAttemptResultDep,
    ListMyAttemptsDep,
    SaveAnswersDep,
    StartAttemptDep,
    Student,
    SubmitAttemptDep,
)
from app.presentation.api.schemas.attempts import AnswersIn, AttemptDetail, AttemptOut, ResultOut

log = logging.getLogger("exam.notify")
router = APIRouter(tags=["Attempts (làm bài thi)"])


@router.post("/api/exams/{exam_id}/attempts", response_model=AttemptDetail)
async def start_attempt(exam_id: int, response: Response, use_case: StartAttemptDep, user: Student):
    """Bắt đầu làm bài. Gọi lại nhiều lần vẫn trả về cùng một bài làm (idempotent) - hỗ trợ F5/vào lại khi rớt mạng."""
    view, created = await use_case.execute(exam_id, user.id)
    if created:
        response.status_code = status.HTTP_201_CREATED
    return AttemptDetail.from_view(view)


@router.get("/api/attempts", response_model=list[AttemptOut])
async def my_attempts(use_case: ListMyAttemptsDep, user: Student):
    return [AttemptOut.from_view(v) for v in await use_case.execute(user.id)]


@router.get("/api/attempts/{attempt_id}", response_model=AttemptDetail)
async def get_attempt(attempt_id: int, use_case: GetAttemptDep, user: Student):
    return AttemptDetail.from_view(await use_case.execute(attempt_id, user.id))


@router.put("/api/attempts/{attempt_id}/answers", response_model=AttemptOut)
async def save_answers(attempt_id: int, data: AnswersIn, use_case: SaveAnswersDep, user: Student):
    """Tự động lưu đáp án (autosave). Mỗi câu chỉ giữ lựa chọn mới nhất."""
    answers = [AnswerChoice(a.question_id, a.choice_id) for a in data.answers]
    return AttemptOut.from_view(await use_case.execute(attempt_id, user.id, answers))


def notify_result(username: str, score: float) -> None:
    """Tác vụ nền: giả lập gửi email kết quả (thực tế: SMTP/queue)."""
    log.info("Đã gửi email kết quả tới %s: %.2f điểm", username, score)


@router.post("/api/attempts/{attempt_id}/submit", response_model=ResultOut)
async def submit(attempt_id: int, background: BackgroundTasks, use_case: SubmitAttemptDep, user: Student):
    result, first_time = await use_case.execute(attempt_id, user.id)
    if first_time:
        background.add_task(notify_result, user.username, result.attempt.score)
    return ResultOut.from_result(result)


@router.get("/api/attempts/{attempt_id}/result", response_model=ResultOut)
async def attempt_result(attempt_id: int, use_case: GetAttemptResultDep, user: CurrentUser):
    return ResultOut.from_result(await use_case.execute(attempt_id, user.id))
