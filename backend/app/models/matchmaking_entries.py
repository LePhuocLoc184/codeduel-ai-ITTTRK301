import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Index, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


if TYPE_CHECKING:
    from app.models.users import User
    from app.models.rooms import Room


class MatchmakingEntry(Base):
    __tablename__ = "matchmaking_entries"
    __table_args__ = ( #khởi tạo chỉ mục đặc biệt (chỉ mục duy nhất có điều kiện)
        Index(
            "uq_matchmaking_searching_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'searching'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    game_mode: Mapped[str] = mapped_column(
        String(32), default="RANKED_1V1", server_default="RANKED_1V1", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="searching", server_default="searching", nullable=False)
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    matched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None)

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="matchmaking_entries")
    room: Mapped["Room | None"] = relationship(
        "Room", back_populates="matchmaking_entries")
