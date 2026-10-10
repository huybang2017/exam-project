"""Hai endpoint mô phỏng I/O chậm 100 ms - dùng để đo sự khác biệt giữa `def` và `async def`."""
import asyncio
import time

from fastapi import APIRouter

router = APIRouter(prefix="/api/demo", tags=["Demo async vs sync"])

IO_SECONDS = 0.1


@router.get("/sync-io")
def sync_io():
    # `def` thường: FastAPI chạy trong threadpool (mặc định tối đa 40 luồng)
    time.sleep(IO_SECONDS)
    return {"mode": "sync"}


@router.get("/async-io")
async def async_io():
    # `async def`: nhường event loop khi chờ I/O, không tốn luồng
    await asyncio.sleep(IO_SECONDS)
    return {"mode": "async"}
