from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, PlainSerializer

Role = Literal["admin", "teacher", "student"]


def _to_naive_utc(v: datetime) -> datetime:
    if v.tzinfo is not None:
        v = v.astimezone(UTC).replace(tzinfo=None)
    return v


# Nhận datetime bất kỳ -> lưu UTC; trả ra luôn có hậu tố Z
UtcDT = Annotated[
    datetime,
    AfterValidator(_to_naive_utc),
    PlainSerializer(lambda v: v.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z"), return_type=str),
]


class Page(BaseModel):
    total: int
    items: list
