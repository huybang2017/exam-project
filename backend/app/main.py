import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import attempts, auth, demo, exams, questions, users, ws
from app.services.grading import auto_submit_expired

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("exam")


async def _expiry_loop() -> None:
    """Tác vụ nền: định kỳ thu các bài đã quá hạn (phòng khi thí sinh đóng trình duyệt)."""
    while True:
        try:
            async with SessionLocal() as db:
                await auto_submit_expired(db)
        except Exception:  # không để vòng lặp nền chết vì một lỗi đơn lẻ
            log.exception("Lỗi khi quét bài quá hạn")
        await asyncio.sleep(settings.expiry_scan_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(_expiry_loop())
    yield
    task.cancel()


app = FastAPI(
    title="Online Exam Management API",
    description="Hệ thống quản lý thi trắc nghiệm trực tuyến - Nhóm 25, môn Các công nghệ lập trình hiện đại.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - start) * 1000:.2f}ms"
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Lỗi không xử lý: %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Lỗi máy chủ nội bộ"}, status_code=500)


for r in (auth.router, users.router, questions.router, exams.router, attempts.router, ws.router, demo.router):
    app.include_router(r)


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok"}
