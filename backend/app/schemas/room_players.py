from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.users import UserBaseResponse


class RoomPlayerBase(BaseModel):
    is_ready: bool = False


class RoomPlayerCreate(RoomPlayerBase):
    room_id: UUID


# --- BỔ SUNG: Cập nhật thông tin/trạng thái người chơi trong phòng ---
class RoomPlayerUpdateRequest(BaseModel):
    score: int | None = Field(
        None, ge=0, description="Cập nhật điểm số trong trận")
    is_ready: bool | None = Field(
        None, description="Cập nhật trạng thái Sẵn sàng / Chưa sẵn sàng")
    elo_change: int | None = Field(
        None, description="Cập nhật cộng/trừ Elo khi kết thúc trận")


class RoomPlayerResponse(RoomPlayerBase):
    id: UUID
    room_id: UUID
    user_id: UUID
    score: int = Field(0, ge=0)
    elo_change: int = Field(0)
    joined_at: datetime
    user: UserBaseResponse | None = None

    model_config = ConfigDict(from_attributes=True)
