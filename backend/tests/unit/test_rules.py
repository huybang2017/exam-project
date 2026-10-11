from datetime import datetime, timedelta

import pytest

from app.domain import rules
from app.domain.entities import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, Attempt, Exam, User
from app.domain.errors import ConflictError, ForbiddenError

NOW = datetime(2026, 10, 10, 8, 0, 0)


def exam(**kw) -> Exam:
    base = dict(title="Đề", description="", duration_minutes=30, start_time=NOW - timedelta(hours=1),
                end_time=NOW + timedelta(hours=1), owner_id=7, id=1)
    return Exam(**{**base, **kw})


def attempt(**kw) -> Attempt:
    base = dict(exam_id=1, user_id=2, started_at=NOW, deadline=NOW + timedelta(minutes=30), id=1)
    return Attempt(**{**base, **kw})


def test_exactly_one_correct():
    assert rules.exactly_one_correct([False, True, False])
    assert not rules.exactly_one_correct([False, False])
    assert not rules.exactly_one_correct([True, True])


def test_ensure_role():
    rules.ensure_role(User("a", "a", ROLE_TEACHER, "h", 1), ROLE_TEACHER, ROLE_ADMIN)
    with pytest.raises(ForbiddenError):
        rules.ensure_role(User("a", "a", ROLE_STUDENT, "h", 1), ROLE_TEACHER, ROLE_ADMIN)


def test_exam_owner_or_admin():
    rules.ensure_exam_owner(exam(), User("t", "t", ROLE_TEACHER, "h", 7))
    rules.ensure_exam_owner(exam(), User("ad", "ad", ROLE_ADMIN, "h", 99))
    with pytest.raises(ForbiddenError):
        rules.ensure_exam_owner(exam(), User("other", "o", ROLE_TEACHER, "h", 8))


def test_window_open():
    rules.ensure_window_open(exam(), NOW)
    with pytest.raises(ForbiddenError, match="Chưa đến giờ thi"):
        rules.ensure_window_open(exam(start_time=NOW + timedelta(minutes=1)), NOW)
    with pytest.raises(ForbiddenError, match="đã kết thúc"):
        rules.ensure_window_open(exam(end_time=NOW - timedelta(minutes=1)), NOW)


def test_deadline_is_capped_by_exam_end():
    assert rules.compute_deadline(NOW, 30, NOW + timedelta(hours=2)) == NOW + timedelta(minutes=30)
    assert rules.compute_deadline(NOW, 30, NOW + timedelta(minutes=10)) == NOW + timedelta(minutes=10)


def test_remaining_seconds():
    assert rules.remaining_seconds(attempt(), NOW) == 1800
    assert rules.remaining_seconds(attempt(), NOW + timedelta(hours=1)) == 0
    assert rules.remaining_seconds(attempt(submitted_at=NOW), NOW) == 0


def test_save_answers_window_with_grace():
    a = attempt()
    rules.ensure_can_save_answers(a, a.deadline + timedelta(seconds=5), 5)
    with pytest.raises(ConflictError, match="hết giờ"):
        rules.ensure_can_save_answers(a, a.deadline + timedelta(seconds=6), 5)
    with pytest.raises(ConflictError, match="đã nộp"):
        rules.ensure_can_save_answers(attempt(submitted_at=NOW), NOW, 5)


def test_to_ten_scale():
    assert rules.to_ten_scale(2, 4) == 5.0
    assert rules.to_ten_scale(1, 3) == 3.33
    assert rules.to_ten_scale(0, 0) == 0.0


def test_publish_rejected_after_end():
    rules.ensure_can_publish(exam(), NOW)
    with pytest.raises(ConflictError):
        rules.ensure_can_publish(exam(end_time=NOW), NOW)
