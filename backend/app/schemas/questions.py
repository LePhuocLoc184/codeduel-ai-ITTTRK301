from uuid import UUID
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class QuestionDifficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class TestCaseItem(BaseModel):
    input: str
    expected_output: str
    is_hidden: bool = False

    @field_validator("expected_output", "input")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class StarterCodeSchema(BaseModel):
    cpp: str = Field(..., min_length=1)
    python: str = Field(..., min_length=1)
    java: str = Field(..., min_length=1)


class QuestionBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10,
                             description="Nội dung Markdown bài toán")
    difficulty: QuestionDifficulty
    time_limit: float = Field(2.0, gt=0.0, le=10.0)
    memory_limit: int = Field(128, gt=0, le=1024)
    starter_code: StarterCodeSchema
    test_cases: list[TestCaseItem] = Field(
        ..., min_length=2, description="Phải có ít nhất 2 testcases (Public & Hidden)")
    generated_by_ai: bool = False


# --- FR-4.1: Input cho AI Problem Generator ---
class AIQuestionGenerateRequest(BaseModel):
    difficulty: QuestionDifficulty
    topic: str = Field(min_length=2, max_length=50,
                       examples=["Array, String, Dynamic Programming"])


class QuestionResponse(QuestionBase):
    id: UUID
    problem_set_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
