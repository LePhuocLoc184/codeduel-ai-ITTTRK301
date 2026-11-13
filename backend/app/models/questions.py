import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING
from sqlalchemy import String, Text, Float, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.problem_sets import ProblemSet
    from app.models.rooms import Room
    from app.models.submissions import Submission


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problem_sets.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    time_limit: Mapped[float] = mapped_column(
        Float, default=2.0, server_default="2.0", nullable=False)
    memory_limit: Mapped[int] = mapped_column(
        Integer, default=128, server_default="128", nullable=False)
    starter_code: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    test_cases: Mapped[list[dict[str, Any]]
                       ] = mapped_column(JSONB, nullable=False)
    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    problem_set: Mapped["ProblemSet"] = relationship(
        "ProblemSet", back_populates="questions")
    rooms: Mapped[list["Room"]] = relationship(
        "Room", back_populates="question")
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission", back_populates="question", cascade="all, delete-orphan")
