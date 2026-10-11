from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        """UTC không kèm tzinfo (khớp cách lưu trong CSDL)."""
        return datetime.now(UTC).replace(tzinfo=None)
