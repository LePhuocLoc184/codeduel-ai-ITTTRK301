import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.users import User
    from app.models.rooms import Room


class RoomPlayer(Base):
    __tablename__ = "room_players"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id",
                         name="uq_room_players_room_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False)
    is_ready: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False)
    elo_change: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="players")
    user: Mapped["User"] = relationship("User", back_populates="room_players")
