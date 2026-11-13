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
    # Đây là kết quả chấm bài, khác HTTP status và trạng thái PLAYING/FINISHED của phòng.
    PENDING = "PENDING"
    PASS = "PASS"
    # Tên ngắn dùng cho luồng Execute mới: sai đáp án, quá thời gian, quá bộ nhớ.
    FAIL = "FAIL"
    TLE = "TLE"
    MLE = "MLE"
    # Giữ tên cũ để vẫn đọc được response/bản ghi đã dùng các trạng thái này.
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    COMPILE_ERROR = "COMPILE_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"


# --- FR-3.2: Chạy thử Code (Run Code - Public Testcases) ---
class CodeRunRequest(BaseModel):
    """Dữ liệu Run: chọn bài và gửi code; user_id luôn lấy từ JWT ở router."""
    question_id: UUID
    language: SubmissionLanguage
    code_content: str = Field(..., min_length=1, description="Mã nguồn từ Monaco Editor")


class PublicTestCaseResult(BaseModel):
    """Một dòng kết quả để frontend hiển thị Console khi chạy thử.

    passed là kết quả đối chiếu đáp án; status cho biết PASS/FAIL/TLE/MLE/...
    để phân biệt sai đáp án với lỗi thực thi. execution_time có đơn vị giây.
    """
    input: str
    expected_output: str
    actual_output: str | None = None
    passed: bool
    execution_time: float | None = None
    status: SubmissionStatus = SubmissionStatus.FAIL
    error_message: str | None = None


class CodeRunResponse(BaseModel):
    """Kết quả tổng của Run và danh sách chi tiết chỉ gồm testcase công khai."""
    status: SubmissionStatus
    results: list[PublicTestCaseResult]
    # Lỗi compile nằm ở cấp bài nộp, khi đó chưa có testcase nào được thực thi.
    compile_error_message: str | None = None
    # Trường chung cho thông báo lỗi tổng hợp; có thể dùng cho nhiều loại lỗi.
    error_message: str | None = None


# --- FR-3.3: Nộp bài chính thức (Submit Code - Hidden Testcases) ---
class SubmissionCreateRequest(BaseModel):
    """Dữ liệu Submit; service phải đối chiếu room_id/question_id với DB.

    Không có user_id trong body: người nộp được xác định bằng Bearer token.
    """
    room_id: UUID
    question_id: UUID
    language: SubmissionLanguage
    code_content: str = Field(..., min_length=1)


class SubmissionResponse(BaseModel):
    """Lịch sử của một bài nộp hợp lệ, kể cả khi code compile/chạy thất bại.

    Không chứa input/expected_output/actual_output của hidden testcase.
    execution_time là tổng giây chạy testcase; memory_used là đỉnh RAM quan sát
    được theo MB. error_message có thể rỗng khi chỉ bị sai đáp án (FAIL).
    """
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

    # Cho phép model_validate đọc trực tiếp thuộc tính của đối tượng Submission ORM.
    model_config = ConfigDict(from_attributes=True)


# --- FR-3.4: Xử lý GameOver & Rating Payload ---
class GameOverBroadcastPayload(BaseModel):
    winner_id: UUID
    loser_id: UUID
    winner_elo_change: int
    loser_elo_change: int
    room_id: UUID
    finished_at: datetime
