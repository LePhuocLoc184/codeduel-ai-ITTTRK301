from typing import Generic, TypeVar, Any
from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: T | None = None
    error: Any | None = None
    timestamp: datetime = datetime.utcnow()
