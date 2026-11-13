from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.users import UserBaseResponse


class ProblemSetBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str | None = Field(None, max_length=255)
    is_hidden: bool = False


class ProblemSetCreate(ProblemSetBase):
    pass



class ProblemSetUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=100)
    description: str | None = Field(None, max_length=255)
    is_hidden: bool | None = None


class ProblemSetResponse(ProblemSetBase):
    id: UUID
    creator_id: UUID | None = None
    created_at: datetime
    creator: UserBaseResponse | None = None

    model_config = ConfigDict(from_attributes=True)
