from datetime import datetime
from typing import Any
from fastapi import status


class AppBaseException(Exception):
    """
    Class Exception Gốc cho toàn bộ lỗi nghiệp vụ trong hệ thống CodeDuel AI.
    Tự động chuẩn hóa cấu hình để sẵn sàng đóng gói theo BaseResponse (7 trường).
    """

    def __init__(
        self,
        message: str = "Đã xảy ra lỗi hệ thống",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
        details: Any | None = None,
        path: str | None = None,
    ):
        super().__init__(message)
        self.success: bool = False
        self.message: str = message
        self.status_code: int = status_code
        self.error_code: str = error_code
        self.data: Any | None = None
        self.error: dict[str, Any] = {
            "code": error_code,
            "details": details or message,
        }
        self.path: str | None = path
        self.timestamp: datetime = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Phương thức convert nhanh Exception thành dictionary chuẩn BaseResponse"""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "path": self.path,
            "timestamp": self.timestamp.isoformat(),
        }


# ==========================================
# CÁC CUSTOM EXCEPTIONS CHO TỪNG PHÂN HỆ
# ==========================================


# 1. Lỗi 400 - Bad Request (Truyền sai dữ liệu, logic nghiệp vụ không cho phép)
class BadRequestException(AppBaseException):
    def __init__(
        self,
        message: str = "Dữ liệu yêu cầu không hợp lệ",
        error_code: str = "BAD_REQUEST",
        details: Any | None = None,
        path: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
            details=details,
            path=path,
        )


# 2. Lỗi 401 - Unauthorized (Chưa đăng nhập, Token sai hoặc hết hạn)
class UnauthorizedException(AppBaseException):
    def __init__(
        self,
        message: str = "Xác thực thất bại hoặc phiên đăng nhập đã hết hạn",
        error_code: str = "UNAUTHORIZED",
        details: Any | None = None,
        path: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            details=details,
            path=path,
        )


# 3. Lỗi 403 - Forbidden (Đã xác thực nhưng không đủ quyền - ví dụ User thường đòi xóa bài của Admin)
class ForbiddenException(AppBaseException):
    def __init__(
        self,
        message: str = "Bạn không có quyền truy cập hoặc thực hiện thao tác này",
        error_code: str = "FORBIDDEN",
        details: Any | None = None,
        path: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=error_code,
            details=details,
            path=path,
        )


# 4. Lỗi 404 - Not Found (Không tìm thấy User, Room, Question, Submission)
class NotFoundException(AppBaseException):
    def __init__(
        self,
        message: str = "Tài nguyên yêu cầu không tồn tại",
        error_code: str = "NOT_FOUND",
        details: Any | None = None,
        path: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code,
            details=details,
            path=path,
        )


# 5. Lỗi 409 - Conflict (Trùng lặp Username, Email, hoặc người chơi đang ở trong phòng khác)
class ConflictException(AppBaseException):
    def __init__(
        self,
        message: str = "Tài nguyên đã tồn tại hoặc xảy ra xung đột trạng thái",
        error_code: str = "CONFLICT",
        details: Any | None = None,
        path: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code,
            details=details,
            path=path,
        )


# 6. Lỗi 422 - Unprocessable Entity (Dành riêng cho lỗi Sandbox chấm code hoặc biên dịch)
class SandboxExecutionException(AppBaseException):
    def __init__(
        self,
        message: str = "Lỗi thực thi mã nguồn trong Sandbox",
        error_code: str = "SANDBOX_ERROR",
        details: Any | None = None,
        path: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=error_code,
            details=details,
            path=path,
        )


# 7. Lỗi 500 - Internal Server Error (Lỗi hệ thống không lường trước được)
class InternalServerErrorException(AppBaseException):
    def __init__(
        self,
        message: str = "Đã xảy ra lỗi nội bộ hệ thống, vui lòng thử lại sau",
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Any | None = None,
        path: str | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=error_code,
            details=details,
            path=path,
        )