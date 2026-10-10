import os
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Phải đặt biến môi trường TRƯỚC khi import app (settings đọc lúc import).
_tmp = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["EXPIRY_SCAN_SECONDS"] = "3600"  # tắt vòng quét nền; test gọi trực tiếp khi cần
os.environ["SECRET_KEY"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


def iso(dt: datetime) -> str:
    return dt.isoformat()


def now_utc() -> datetime:
    return datetime.now(UTC)


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str) -> str:
    r = client.post("/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def teacher(client):
    async def create():
        async with SessionLocal() as db:
            db.add(User(username="teacher_t", full_name="GV Test", role="teacher",
                        password_hash=hash_password("Teacher@123")))
            await db.commit()

    client.portal.call(create)
    return headers(login(client, "teacher_t", "Teacher@123"))


@pytest.fixture
def new_student(client):
    """Nhà máy tạo sinh viên mới (mỗi test một người để không đụng UNIQUE(exam, user))."""

    def make():
        username = f"sv_{uuid.uuid4().hex[:10]}"
        r = client.post("/api/auth/register", json={"username": username, "password": "Student@123", "full_name": "SV Test"})
        assert r.status_code == 201, r.text
        return username, headers(login(client, username, "Student@123"))

    return make


def make_exam(client, teacher, *, start=None, end=None, publish=True, n_questions=4, title="Đề test"):
    """Tạo n câu hỏi (4 lựa chọn, đáp án đúng là lựa chọn thứ hai) và một đề. Trả về dict mô tả đề."""
    questions = []
    for i in range(n_questions):
        r = client.post("/api/questions", headers=teacher, json={
            "content": f"Câu hỏi số {i + 1}?",
            "choices": [{"text": "A"}, {"text": "B", "is_correct": True}, {"text": "C"}, {"text": "D"}],
        })
        assert r.status_code == 201, r.text
        q = r.json()
        questions.append({
            "id": q["id"],
            "correct": next(c["id"] for c in q["choices"] if c["is_correct"]),
            "wrong": next(c["id"] for c in q["choices"] if not c["is_correct"]),
        })
    now = now_utc()
    r = client.post("/api/exams", headers=teacher, json={
        "title": title, "duration_minutes": 30,
        "start_time": iso(start or now - timedelta(hours=1)), "end_time": iso(end or now + timedelta(days=1)),
        "items": [{"question_id": q["id"], "points": 1} for q in questions],
    })
    assert r.status_code == 201, r.text
    exam = r.json()
    if publish:
        assert client.post(f"/api/exams/{exam['id']}/publish", headers=teacher).status_code == 200
    return {"id": exam["id"], "questions": questions}


@pytest.fixture(scope="session")
def exam(client, teacher):
    return make_exam(client, teacher)
