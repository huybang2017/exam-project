import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.application.use_cases.attempts import AutoSubmitExpiredAttempts
from app.infrastructure.config import settings
from app.infrastructure.db.engine import init_db
from app.presentation.api.dependencies import clock, uow_factory
from app.presentation.api.error_handlers import register_error_handlers
from app.presentation.api.routers import attempts, auth, demo, exams, questions, users
from app.presentation.api.ws import exam_clock

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("exam")


async def _expiry_loop() -> None:
    """Tác vụ nền: định kỳ thu các bài đã quá hạn (phòng khi thí sinh đóng trình duyệt giữa chừng)."""
    while True:
        try:
            async with uow_factory() as uow:
                count = await AutoSubmitExpiredAttempts(uow, clock).execute()
            if count:
                log.info("Tự động thu %d bài quá hạn", count)
        except Exception:  # không để vòng lặp nền chết vì một lỗi đơn lẻ
            log.exception("Lỗi khi quét bài quá hạn")
        await asyncio.sleep(settings.expiry_scan_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(_expiry_loop())
    yield
    task.cancel()


def create_app() -> FastAPI:
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

    register_error_handlers(app)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("Lỗi không xử lý: %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Lỗi máy chủ nội bộ"}, status_code=500)

    for router in (auth.router, users.router, questions.router, exams.router, attempts.router,
                   exam_clock.router, demo.router):
        app.include_router(router)

    @app.get("/health", tags=["System"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
