import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.application.use_cases.attempts import ExpireAttempt, GetAttemptForClock
from app.application.use_cases.auth import Authenticate
from app.domain.errors import DomainError
from app.presentation.api.dependencies import clock, tokens, uow_factory

router = APIRouter(tags=["WebSocket"])

CHECK_EVERY = 5  # cứ 5 giây mới hỏi DB xem bài đã được nộp ở nơi khác chưa


@router.websocket("/ws/attempts/{attempt_id}")
async def attempt_clock(ws: WebSocket, attempt_id: int, token: str):
    """Đồng hồ thời gian thực do SERVER điều khiển - thí sinh không thể sửa giờ ở client.

    Mỗi giây gửi {"remaining": <giây>}; khi hết giờ tự thu bài và gửi {"event": "expired", "score": ...}.
    Không giữ phiên DB trong suốt buổi thi (sẽ chiếm connection pool): chỉ mở Unit of Work ngắn khi cần.
    """
    try:
        async with uow_factory() as uow:
            user = await Authenticate(uow, tokens).execute(token)
            deadline = (await GetAttemptForClock(uow).execute(attempt_id, user.id)).deadline
    except DomainError:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws.accept()
    try:
        tick = 0
        while True:
            if tick % CHECK_EVERY == 0:
                async with uow_factory() as uow:
                    attempt = await GetAttemptForClock(uow).execute(attempt_id, user.id)
                if attempt.is_submitted:
                    await ws.send_json({"event": "submitted", "score": attempt.score})
                    break
            if (deadline - clock.now()).total_seconds() <= 0:
                async with uow_factory() as uow:
                    attempt = await ExpireAttempt(uow, clock).execute(attempt_id)
                await ws.send_json({"event": "expired", "score": attempt.score})
                break
            await ws.send_json({"remaining": int((deadline - clock.now()).total_seconds())})
            tick += 1
            await asyncio.sleep(1)
        await ws.close()
    except WebSocketDisconnect:
        pass
