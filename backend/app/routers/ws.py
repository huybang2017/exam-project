import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from app.database import SessionLocal
from app.deps import user_from_token
from app.models import Attempt, utcnow
from app.services.grading import submit_attempt

router = APIRouter(tags=["WebSocket"])

CHECK_EVERY = 5  # cứ 5 giây mới hỏi DB xem bài đã được nộp ở nơi khác chưa


@router.websocket("/ws/attempts/{attempt_id}")
async def attempt_clock(ws: WebSocket, attempt_id: int, token: str):
    """Đồng hồ thời gian thực do SERVER điều khiển - thí sinh không thể sửa giờ ở client.

    Mỗi giây gửi {"remaining": <giây>}; khi hết giờ tự thu bài và gửi {"event": "expired", "score": ...}.
    Không giữ phiên DB trong suốt buổi thi (sẽ chiếm connection pool): chỉ mở phiên ngắn khi cần.
    """
    async with SessionLocal() as db:
        try:
            user = await user_from_token(token, db)
        except HTTPException:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        attempt = await db.get(Attempt, attempt_id)
        if attempt is None or attempt.user_id != user.id:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        deadline = attempt.deadline  # phiên DB đóng ngay sau khối này

    await ws.accept()
    try:
        tick = 0
        while True:
            if tick % CHECK_EVERY == 0:
                async with SessionLocal() as db:
                    a = await db.get(Attempt, attempt_id)
                    if a.submitted_at is not None:
                        await ws.send_json({"event": "submitted", "score": a.score})
                        break
            remaining = (deadline - utcnow()).total_seconds()
            if remaining <= 0:
                async with SessionLocal() as db:
                    a = await db.get(Attempt, attempt_id)
                    await submit_attempt(db, a, auto=True, at=a.deadline)
                    await ws.send_json({"event": "expired", "score": a.score})
                break
            await ws.send_json({"remaining": int(remaining)})
            tick += 1
            await asyncio.sleep(1)
        await ws.close()
    except WebSocketDisconnect:
        pass
