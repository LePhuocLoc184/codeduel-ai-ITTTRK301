from uuid import UUID
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.users import UserBaseResponse
from app.schemas.questions import QuestionResponse


class GameMode(str, Enum):
    RANKED_1V1 = "RANKED_1V1"
    CUSTOM_1V1 = "CUSTOM_1V1"


class RoomStatus(str, Enum):
    WAITING = "WAITING"
    PLAYING = "PLAYING"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


# --- FR-2.1: Tạo phòng Custom ---
class CustomRoomCreateRequest(BaseModel):
    problem_set_id: UUID | None = None


class JoinRoomRequest(BaseModel):
    room_code: str = Field(..., min_length=6, max_length=6, description="Mã PIN 6 ký tự")


# --- WebSocket Event Protocols (FR-2.3) ---
class WSEventType(str, Enum):
    JOIN_ROOM = "JOIN_ROOM"
    PLAYER_READY = "PLAYER_READY"
    COUNTDOWN_START = "COUNTDOWN_START"
    PLAYER_TYPING = "PLAYER_TYPING"
    MATCH_FOUND = "MATCH_FOUND"
    GAME_OVER = "GAME_OVER"
    ERROR = "ERROR"


class WSPayload(BaseModel):
    event: WSEventType
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- Post-Match AI Review (FR-4.2) ---
class AIReviewReport(BaseModel):
    time_complexity_analysis: str
    space_complexity_analysis: str
    clean_code_evaluation: str
    optimized_solution: dict[str, str]  # Code mẫu chuẩn cho từng ngôn ngữ


class RoomResponse(BaseModel):
    id: UUID
    code: str = Field(..., min_length=6, max_length=10,
                      description="Mã PIN 6 ký tự độc nhất (VD: CDUEL1)")
    host_id: UUID
    problem_set_id: UUID | None = None
    question_id: UUID | None = None
    game_mode: GameMode
    status: RoomStatus
    rating_applied: bool = False
    ai_review: AIReviewReport | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    host: UserBaseResponse | None = None
    question: QuestionResponse | None = None

    model_config = ConfigDict(from_attributes=True)
