from fastapi import APIRouter, Depends, status

from app.core.exceptions import InternalServerErrorException
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.response import BaseResponse
from app.schemas.runner import CodeSaveRequest, CodeSaveResponse
from app.services.runner import CODE_BACKUP_DIR, save_code_file


router = APIRouter(prefix="/api/v1/runner", tags=["Runner"])


# AC 1: Nối schema nhập mã với service lưu file; có thể nhập thử trực tiếp trên /docs.
@router.post(
    "/save-code",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[CodeSaveResponse],
)
def save_code(
    payload: CodeSaveRequest,
    current_user: User = Depends(get_current_user),
) -> BaseResponse[CodeSaveResponse]:
    # Endpoint đồng bộ được FastAPI chạy trong thread pool để ghi file không chặn event loop.
    try:
        # Chỉ lấy UUID từ user đăng nhập qua Bearer token, không lấy từ request body.
        code_path = save_code_file(
            payload.code_content, payload.language, current_user.id
        )
    except OSError as exc:
        raise InternalServerErrorException(message="Không thể lưu mã nguồn") from exc

    return BaseResponse(
        message="Đã lưu mã nguồn thành công",
        data=CodeSaveResponse(
            user_id=current_user.id,
            language=payload.language,
            file_path=code_path.relative_to(CODE_BACKUP_DIR).as_posix(),
        ),
    )
