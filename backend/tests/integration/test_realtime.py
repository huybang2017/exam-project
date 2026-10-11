import pytest
from starlette.websockets import WebSocketDisconnect

from app.presentation.api.ws import exam_clock as ws_module

from .conftest import login


def test_t16_websocket_clock(client, exam, new_student, monkeypatch):
    monkeypatch.setattr(ws_module, "CHECK_EVERY", 1)  # kiểm tra DB mỗi giây để test nhanh
    username, student = new_student()
    token = login(client, username, "Student@123")
    attempt_id = client.post(f"/api/exams/{exam['id']}/attempts", headers=student).json()["id"]

    with client.websocket_connect(f"/ws/attempts/{attempt_id}?token={token}") as ws:
        first = ws.receive_json()
        assert 0 < first["remaining"] <= 30 * 60
        client.post(f"/api/attempts/{attempt_id}/submit", headers=student)
        events = []
        with pytest.raises(WebSocketDisconnect) as closed:  # server tự đóng sau sự kiện kết thúc
            for _ in range(5):
                events.append(ws.receive_json())
    assert closed.value.code == 1000
    assert events[-1]["event"] == "submitted"

    with pytest.raises(WebSocketDisconnect) as err:
        with client.websocket_connect(f"/ws/attempts/{attempt_id}?token=token-sai") as ws:
            ws.receive_text()
    assert err.value.code == 1008
