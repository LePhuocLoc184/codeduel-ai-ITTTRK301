import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.rooms import Room
    from app.models.users import User
    from app.models.questions import Question


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        Index("idx_submissions_room_user", "room_id", "user_id"),
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
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    code_content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    # Nâng lên 32 ký tự cho TLE, MLE...
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    passed_test_cases: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    total_test_cases: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    execution_time: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None
    )
    memory_used: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    room: Mapped["Room"] = relationship("Room", back_populates="submissions")
    user: Mapped["User"] = relationship("User", back_populates="submissions")
    question: Mapped["Question"] = relationship(
        "Question", back_populates="submissions"
    )
