from datetime import timedelta

from sqlalchemy import update

from app.application.use_cases.attempts import AutoSubmitExpiredAttempts
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.engine import SessionLocal
from app.infrastructure.db.orm_models import AttemptORM
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

from .conftest import make_exam, now_utc


def _start(client, student, exam_id):
    return client.post(f"/api/exams/{exam_id}/attempts", headers=student)


def test_t04_question_needs_exactly_one_correct(client, teacher):
    for choices in (
        [{"text": "A"}, {"text": "B"}],  # 0 đáp án đúng
        [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": True}],  # 2 đáp án đúng
    ):
        r = client.post("/api/questions", headers=teacher, json={"content": "Câu hỏi sai?", "choices": choices})
        assert r.status_code == 422


def test_t05_teacher_creates_and_publishes_exam(client, teacher):
    exam = make_exam(client, teacher, publish=False, title="Đề nháp T05")
    detail = client.get(f"/api/exams/{exam['id']}", headers=teacher).json()
    assert detail["is_published"] is False and detail["question_count"] == 4
    r = client.post(f"/api/exams/{exam['id']}/publish", headers=teacher)
    assert r.status_code == 200 and r.json()["is_published"] is True


def test_t06_student_sees_only_published(client, teacher, exam, new_student):
    draft = make_exam(client, teacher, publish=False, title="Đề nháp T06")
    _, student = new_student()
    ids = {e["id"] for e in client.get("/api/exams", headers=student).json()}
    assert exam["id"] in ids
    assert draft["id"] not in ids


def test_t07_start_is_idempotent(client, exam, new_student):
    _, student = new_student()
    first, second = _start(client, student, exam["id"]), _start(client, student, exam["id"])
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]


def test_t08_questions_hide_correct_answer(client, exam, new_student):
    _, student = new_student()
    r = _start(client, student, exam["id"])
    assert r.status_code == 201
    assert "is_correct" not in r.text
    assert len(r.json()["questions"]) == 4


def test_t09_save_answer_of_other_question_rejected(client, exam, new_student):
    _, student = new_student()
    attempt = _start(client, student, exam["id"]).json()
    q0, q1 = exam["questions"][0], exam["questions"][1]
    r = client.put(f"/api/attempts/{attempt['id']}/answers", headers=student,
                   json={"answers": [{"question_id": q0["id"], "choice_id": q1["correct"]}]})
    assert r.status_code == 422


def _answer_two_of_four(client, exam, student):
    attempt = _start(client, student, exam["id"]).json()
    qs = exam["questions"]
    answers = [
        {"question_id": qs[0]["id"], "choice_id": qs[0]["correct"]},
        {"question_id": qs[1]["id"], "choice_id": qs[1]["correct"]},
        {"question_id": qs[2]["id"], "choice_id": qs[2]["wrong"]},
    ]  # câu 4 bỏ trống
    assert client.put(f"/api/attempts/{attempt['id']}/answers", headers=student, json={"answers": answers}).status_code == 200
    return attempt["id"]


def test_t10_submit_and_grade(client, exam, new_student):
    _, student = new_student()
    attempt_id = _answer_two_of_four(client, exam, student)
    r = client.post(f"/api/attempts/{attempt_id}/submit", headers=student)
    assert r.status_code == 200
    body = r.json()
    assert (body["correct"], body["total"]) == (2, 4)
    assert body["score"] == 5.0  # 2/4 câu đúng, thang 10
    assert body["auto_submitted"] is False


def test_t11_submit_twice_keeps_result(client, exam, new_student):
    _, student = new_student()
    attempt_id = _answer_two_of_four(client, exam, student)
    a = client.post(f"/api/attempts/{attempt_id}/submit", headers=student).json()
    b = client.post(f"/api/attempts/{attempt_id}/submit", headers=student).json()
    assert a["score"] == b["score"] and a["submitted_at"] == b["submitted_at"]


def test_t12_cannot_save_after_submit(client, exam, new_student):
    _, student = new_student()
    attempt_id = _answer_two_of_four(client, exam, student)
    client.post(f"/api/attempts/{attempt_id}/submit", headers=student)
    q = exam["questions"][3]
    r = client.put(f"/api/attempts/{attempt_id}/answers", headers=student,
                   json={"answers": [{"question_id": q["id"], "choice_id": q["correct"]}]})
    assert r.status_code == 409


def test_t13_start_outside_window_rejected(client, teacher, new_student):
    now = now_utc()
    future = make_exam(client, teacher, start=now + timedelta(hours=2), end=now + timedelta(hours=4), title="Đề tương lai")
    _, student = new_student()
    assert _start(client, student, future["id"]).status_code == 403


def test_t14_cannot_read_other_students_attempt(client, exam, new_student):
    _, owner = new_student()
    _, other = new_student()
    attempt_id = _start(client, owner, exam["id"]).json()["id"]
    assert client.get(f"/api/attempts/{attempt_id}", headers=owner).status_code == 200
    assert client.get(f"/api/attempts/{attempt_id}", headers=other).status_code == 404


def test_t15_expired_attempt_is_auto_submitted(client, exam, new_student):
    _, student = new_student()
    attempt_id = _answer_two_of_four(client, exam, student)

    async def expire_and_scan():
        clock = SystemClock()
        async with SessionLocal() as db:  # kéo lùi hạn nộp để giả lập bài đã quá giờ
            await db.execute(
                update(AttemptORM).where(AttemptORM.id == attempt_id).values(deadline=clock.now() - timedelta(minutes=1))
            )
            await db.commit()
        async with SqlAlchemyUnitOfWork(SessionLocal) as uow:
            return await AutoSubmitExpiredAttempts(uow, clock).execute()

    assert client.portal.call(expire_and_scan) >= 1
    result = client.get(f"/api/attempts/{attempt_id}/result", headers=student)
    assert result.status_code == 200
    assert result.json()["auto_submitted"] is True and result.json()["score"] == 5.0


def test_t18_export_results_csv(client, teacher, exam, new_student):
    username, student = new_student()
    attempt_id = _answer_two_of_four(client, exam, student)
    client.post(f"/api/attempts/{attempt_id}/submit", headers=student)
    r = client.get(f"/api/exams/{exam['id']}/results.csv", headers=teacher)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.content.decode("utf-8-sig").splitlines()
    assert lines[0] == "username,full_name,score,submitted_at,auto_submitted"
    assert any(line.startswith(f"{username},") for line in lines[1:])
