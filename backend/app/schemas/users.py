from uuid import UUID
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Any


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class RankBadge(str, Enum):
    BRONZE = "BRONZE"      # < 1300
    SILVER = "SILVER"      # 1300 - 1499
    GOLD = "GOLD"          # 1500 - 1699
    DIAMOND = "DIAMOND"    # >= 1700


# --- FR-1.1: Đăng ký Tài khoản ---
class UserRegisterSchema(BaseModel):
    username: str
    email: str
    password: str = Field(..., min_length=8, description="Mật khẩu tối thiểu 8 ký tự")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        # Check ít nhất 1 chữ hoa
        if not any(char.isupper() for char in value):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 ký tự viết hoa (A-Z)")

        # Check ít nhất 1 chữ số
        if not any(char.isdigit() for char in value):
            raise ValueError("Mật khẩu phải chứa ít nhất 1 chữ số (0-9)")

        return value


# --- FR-1.2: Đăng nhập & Authentication ---
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserBaseResponse"


# --- Response Schemas Cơ bản & Dashboard ---
class UserBaseResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    avatar_url: str | None = None
    rating: int = Field(1200, ge=0)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FR-1.3: Profile & Dashboard ---
class RecentMatchItem(BaseModel):
    room_id: UUID
    game_mode: str
    is_win: bool
    elo_change: int
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileDashboardResponse(UserBaseResponse):
    rated_games: int = Field(0, ge=0)
    wins: int = Field(0, ge=0)
    win_rate: float = Field(0.0, ge=0.0, le=100.0)
    rank_badge: RankBadge
    recent_matches: list[RecentMatchItem] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator("win_rate", mode="before")
    @classmethod
    def calculate_win_rate(cls, v: Any, info) -> float:
        # Tự động tính tỷ lệ thắng nếu truyền từ ORM Model
        wins = info.data.get("wins", 0)
        rated_games = info.data.get("rated_games", 0)
        if rated_games > 0:
            return round((wins / rated_games) * 100, 2)
        return 0.0

    @field_validator("rank_badge", mode="before")
    @classmethod
    def compute_rank_badge(cls, v: Any, info) -> RankBadge:
        rating = info.data.get("rating", 1200)
        if rating >= 1700:
            return RankBadge.DIAMOND
        elif rating >= 1500:
            return RankBadge.GOLD
        elif rating >= 1300:
            return RankBadge.SILVER
        return RankBadge.BRONZE


TokenResponse.model_rebuild()


# --- FR-1.4: Leaderboard ---
class LeaderboardItemResponse(BaseModel):
    rank: int = Field(..., ge=1, le=100)
    id: UUID
    avatar_url: str | None = None
    username: str
    rating: int
    rated_games: int
    wins: int
    win_rate: float
    rank_badge: RankBadge

    model_config = ConfigDict(from_attributes=True)
