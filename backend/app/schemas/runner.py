from typing import Literal, TypedDict
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.submissions import SubmissionLanguage


# AC 3.2: TypedDict giữ cấu trúc dictionary trả về từ service biên dịch.
class CompileResult(TypedDict):
    status: Literal["READY", "COMPILE_ERROR"]
    error: str | None
    executable_path: str | None


# AC 1: Dữ liệu nhập từ người dùng trên API /docs gồm mã nguồn và ngôn ngữ.
class CodeSaveRequest(BaseModel):
    code_content: str = Field(..., min_length=1, description="Mã nguồn cần lưu")
    language: SubmissionLanguage

    @field_validator("code_content")
    @classmethod
    def validate_code_content(cls, value: str) -> str:
        # Kiểm tra mã rỗng nhưng giữ nguyên thụt lề và xuống dòng của mã nguồn.
        if not value.strip():
            raise ValueError("Mã nguồn không được để trống")
        return value


class CodeSaveResponse(BaseModel):
    # UUID của user đã xác thực, được lấy ở router thay vì người dùng tự nhập.
    user_id: UUID
    language: SubmissionLanguage
    # Đường dẫn tương đối tính từ backend/code_backup/.
    file_path: str
