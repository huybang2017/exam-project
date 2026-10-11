"""Lỗi nghiệp vụ. Tầng trình bày (presentation) ánh xạ chúng sang mã HTTP ở một chỗ duy nhất."""


class DomainError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """Không tìm thấy (404)."""


class UnauthorizedError(DomainError):
    """Chưa đăng nhập hoặc token sai (401)."""


class ForbiddenError(DomainError):
    """Không đủ quyền hoặc ngoài khung giờ cho phép (403)."""


class ConflictError(DomainError):
    """Trạng thái hiện tại không cho phép thao tác (409)."""


class InvalidError(DomainError):
    """Dữ liệu vi phạm quy tắc nghiệp vụ (422)."""


class TooManyRequestsError(DomainError):
    """Vượt giới hạn tần suất (429)."""


class DuplicateAttemptError(ConflictError):
    """Thí sinh đã có bài làm cho đề này (vi phạm UNIQUE(exam_id, user_id))."""

    def __init__(self) -> None:
        super().__init__("Thí sinh đã có bài làm cho đề này")
