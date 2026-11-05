import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.users import User
    from app.models.problem_sets import ProblemSet
    from app.models.questions import Question
    from app.models.room_players import RoomPlayer
    from app.models.submissions import Submission
    from app.models.matchmaking_entries import MatchmakingEntry


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(
        # FR-2.1: Mã PIN 6 ký tự (VD: CDUEL1)
        String(6), unique=True, nullable=False, index=True
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    problem_set_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problem_sets.id", ondelete="SET NULL"), nullable=True, default=None
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, default=None
    )
    game_mode: Mapped[str] = mapped_column(
        String(32), default="RANKED_1V1", server_default="RANKED_1V1", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="WAITING", server_default="WAITING", nullable=False
    )
    rating_applied: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    ai_review: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=None  # FR-4.2: Lưu Post-Match AI Review JSON
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Relationships
    host: Mapped["User"] = relationship("User", back_populates="hosted_rooms")
    problem_set: Mapped["ProblemSet | None"] = relationship(
        "ProblemSet", back_populates="rooms"
    )
    question: Mapped["Question | None"] = relationship(
        "Question", back_populates="rooms"
    )
    players: Mapped[list["RoomPlayer"]] = relationship(
        "RoomPlayer", back_populates="room", cascade="all, delete-orphan"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="room", cascade="all, delete-orphan"
    )
    matchmaking_entries: Mapped[list["MatchmakingEntry"]] = relationship(
        "MatchmakingEntry", back_populates="room"
    )
