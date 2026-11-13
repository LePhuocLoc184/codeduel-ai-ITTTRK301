import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.matchmaking_entries import MatchmakingEntry
    from app.models.problem_sets import ProblemSet
    from app.models.room_players import RoomPlayer
    from app.models.rooms import Room
    from app.models.submissions import Submission


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # PostgreSQL tự động hỗ trợ quét B-Tree Index theo 2 chiều ASC/DESC
        Index("idx_users_rating", "rating"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), default="user", server_default="user", nullable=False
    )
    rating: Mapped[int] = mapped_column(
        Integer, default=1200, server_default="1200", nullable=False
    )
    rated_games: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    wins: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    hosted_rooms: Mapped[list["Room"]] = relationship(
        "Room", back_populates="host"
    )
    created_problem_sets: Mapped[list["ProblemSet"]] = relationship(
        "ProblemSet", back_populates="creator"
    )
    room_players: Mapped[list["RoomPlayer"]] = relationship(
        "RoomPlayer", back_populates="user", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="user", cascade="all, delete-orphan"
    )
    matchmaking_entries: Mapped[list["MatchmakingEntry"]] = relationship(
        "MatchmakingEntry", back_populates="user", cascade="all, delete-orphan"
    )
