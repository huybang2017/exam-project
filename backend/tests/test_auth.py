import uuid

from app import deps

from .conftest import headers, login


def test_t01_register_then_login(client):
    username = f"sv_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register", json={"username": username, "password": "Abc12345", "full_name": "Nguyễn Văn A"})
    assert r.status_code == 201
    assert r.json()["role"] == "student"
    token = login(client, username, "Abc12345")
    me = client.get("/api/auth/me", headers=headers(token))
    assert me.status_code == 200 and me.json()["username"] == username


def test_t02_login_wrong_password(client, new_student):
    username, _ = new_student()
    r = client.post("/api/auth/login", data={"username": username, "password": "sai-mat-khau"})
    assert r.status_code == 401


def test_t03_student_cannot_create_question(client, new_student):
    _, student = new_student()
    r = client.post("/api/questions", headers=student, json={
        "content": "Không được phép?", "choices": [{"text": "A", "is_correct": True}, {"text": "B"}],
    })
    assert r.status_code == 403


def test_t17_login_rate_limit(client, new_student, monkeypatch):
    username, _ = new_student()
    monkeypatch.setattr(deps.settings, "rate_limit_enabled", True)
    deps._login_hits.clear()
    codes = [client.post("/api/auth/login", data={"username": username, "password": "sai"}).status_code for _ in range(11)]
    deps._login_hits.clear()
    assert codes[:10] == [401] * 10
    assert codes[10] == 429
