from uuid import UUID
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict
from app.schemas.users import UserBaseResponse
from app.schemas.rooms import RoomResponse, GameMode


class MatchmakingStatus(str, Enum):
    SEARCHING = "searching"
    MATCHED = "matched"
    CANCELLED = "cancelled"


class MatchmakingJoinRequest(BaseModel):
    game_mode: GameMode = GameMode.RANKED_1V1


class MatchmakingEntryResponse(BaseModel):
    id: UUID
    user_id: UUID
    game_mode: GameMode
    status: MatchmakingStatus
    room_id: UUID | None = None
    created_at: datetime
    matched_at: datetime | None = None

    user: UserBaseResponse | None = None
    room: RoomResponse | None = None

    model_config = ConfigDict(from_attributes=True)
