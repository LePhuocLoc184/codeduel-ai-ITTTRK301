import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.users import User
    from app.models.questions import Question
    from app.models.rooms import Room


class ProblemSet(Base):
    __tablename__ = "problem_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None)
    creator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None
    )
    is_hidden: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    creator: Mapped["User | None"] = relationship(
        "User", back_populates="created_problem_sets")
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="problem_set", cascade="all, delete-orphan")
    rooms: Mapped[list["Room"]] = relationship(
        "Room", back_populates="problem_set")
