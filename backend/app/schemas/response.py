from typing import Generic, TypeVar, Any
from pydantic import BaseModel, Field
from datetime import UTC, datetime

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: T | None = None
    error: Any | None = None
    path: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
