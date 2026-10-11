"""Quy tắc nghiệp vụ là hàm thuần: không I/O, không đọc đồng hồ (giờ hiện tại được truyền vào)."""
from datetime import datetime, timedelta

from app.domain.entities import ROLE_ADMIN, Attempt, Exam, User
from app.domain.errors import ConflictError, ForbiddenError


def exactly_one_correct(flags: list[bool]) -> bool:
    return sum(flags) == 1


def ensure_role(user: User, *roles: str) -> None:
    if user.role not in roles:
        raise ForbiddenError("Bạn không có quyền thực hiện thao tác này")


def ensure_exam_owner(exam: Exam, user: User) -> None:
    if user.role != ROLE_ADMIN and exam.owner_id != user.id:
        raise ForbiddenError("Đề thi này thuộc giáo viên khác")


def ensure_window_open(exam: Exam, now: datetime) -> None:
    if now < exam.start_time:
        raise ForbiddenError("Chưa đến giờ thi")
    if now > exam.end_time:
        raise ForbiddenError("Kỳ thi đã kết thúc")


def ensure_can_publish(exam: Exam, now: datetime) -> None:
    if exam.end_time <= now:
        raise ConflictError("Đề đã quá thời gian kết thúc")


def compute_deadline(now: datetime, duration_minutes: int, exam_end: datetime) -> datetime:
    return min(now + timedelta(minutes=duration_minutes), exam_end)


def remaining_seconds(attempt: Attempt, now: datetime) -> int:
    if attempt.is_submitted:
        return 0
    return max(0, int((attempt.deadline - now).total_seconds()))


def ensure_can_save_answers(attempt: Attempt, now: datetime, grace_seconds: int) -> None:
    if attempt.is_submitted:
        raise ConflictError("Bài đã nộp, không thể sửa đáp án")
    if now > attempt.deadline + timedelta(seconds=grace_seconds):
        raise ConflictError("Đã hết giờ làm bài")


def to_ten_scale(earned_points: float, total_points: float) -> float:
    return round(earned_points / total_points * 10, 2) if total_points else 0.0
