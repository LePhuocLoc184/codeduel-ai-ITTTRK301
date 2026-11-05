from datetime import UTC, datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

from app.core.exceptions import AppBaseException
# Import BaseResponse chuẩn của bạn
from app.schemas.response import BaseResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app):

    # 1. Bắt các Custom App Exception (400, 401, 403, 404, 409...)
    @app.exception_handler(AppBaseException)
    async def custom_exception_handler(request: Request, exc: AppBaseException):
        exc.path = request.url.path
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()  
        )

    # 2. Bắt lỗi Validation 422 từ Pydantic (Khi truyền sai body request)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        details = []
        for err in errors:
            details.append({
                "loc": " -> ".join([str(x) for x in err.get("loc", [])]),
                "msg": err.get("msg"),
                "type": err.get("type")
            })

        
        response_payload = BaseResponse[None]( # Generic Type
            success=False,
            message="Dữ liệu đầu vào không hợp lệ",
            data=None,
            error={
                "code": "VALIDATION_ERROR",
                "details": details
            },
            path=request.url.path,
            timestamp=datetime.now(UTC)
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_payload.model_dump(mode="json")
        )

    # 3. Bắt lỗi không lường trước (Crash 500)
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled request error: %s %s",
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        response_payload = BaseResponse[None]( # Generic Type
            success=False,
            message="Đã xảy ra lỗi hệ thống không xác định",
            data=None,
            error={
                "code": "INTERNAL_SERVER_ERROR",
                "details": str(exc)
            },
            path=request.url.path,
            timestamp=datetime.now(UTC)
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_payload.model_dump(mode="json")
        )
