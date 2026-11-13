from uuid import UUID
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator


class SubmissionLanguage(str, Enum):
    # AC 1.2: Chấp nhận cả c và cpp khi nhận mã nguồn.
    C = "c"
    CPP = "cpp"
    PYTHON = "python"
    JAVA = "java"


class SubmissionStatus(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    COMPILE_ERROR = "COMPILE_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"


# --- FR-3.2: Chạy thử Code (Run Code - Public Testcases) ---
class CodeRunRequest(BaseModel):
    question_id: UUID
    language: SubmissionLanguage
    code_content: str = Field(..., min_length=1, description="Mã nguồn từ Monaco Editor")


class PublicTestCaseResult(BaseModel):
    input: str
    expected_output: str
    actual_output: str | None = None
    passed: bool
    execution_time: float | None = None


class CodeRunResponse(BaseModel):
    status: SubmissionStatus
    results: list[PublicTestCaseResult]
    compile_error_message: str | None = None


# --- FR-3.3: Nộp bài chính thức (Submit Code - Hidden Testcases) ---
class SubmissionCreateRequest(BaseModel):
    room_id: UUID
    question_id: UUID
    language: SubmissionLanguage
    code_content: str = Field(..., min_length=1)


class SubmissionResponse(BaseModel):
    id: UUID
    room_id: UUID
    user_id: UUID
    question_id: UUID
    code_content: str
    language: SubmissionLanguage
    status: SubmissionStatus
    passed_test_cases: int = Field(..., ge=0)
    total_test_cases: int = Field(..., ge=0)
    execution_time: float | None = Field(None, ge=0.0)
    memory_used: float | None = Field(None, ge=0.0)
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- FR-3.4: Xử lý GameOver & Rating Payload ---
class GameOverBroadcastPayload(BaseModel):
    winner_id: UUID
    loser_id: UUID
    winner_elo_change: int
    loser_elo_change: int
    room_id: UUID
    finished_at: datetime
