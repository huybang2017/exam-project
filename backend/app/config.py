from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình đọc từ biến môi trường / file .env (12-factor)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Mặc định chạy local bằng SQLite; docker-compose ghi đè sang PostgreSQL.
    database_url: str = "sqlite+aiosqlite:///./exam.db"
    db_pool_size: int = 20  # chỉ áp dụng cho PostgreSQL
    db_max_overflow: int = 20

    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    token_expire_minutes: int = 120

    cache_enabled: bool = True
    cache_ttl_seconds: int = 60

    rate_limit_enabled: bool = True
    login_rate_limit: int = 10  # số lần đăng nhập / cửa sổ
    login_rate_window_seconds: int = 60

    expiry_scan_seconds: float = 5.0  # chu kỳ quét bài hết giờ
    submit_grace_seconds: int = 5  # độ trễ mạng cho phép khi lưu đáp án

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
