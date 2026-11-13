"""Hai API chấm code: router nhận/kiểm tra body, service xử lý nghiệp vụ và DB."""
from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.response import BaseResponse
from app.schemas.submissions import CodeRunRequest, CodeRunResponse, SubmissionCreateRequest, SubmissionResponse
from app.services import execute

# Prefix ghép với /run hoặc /submit thành đường dẫn đầy đủ cho frontend.
router = APIRouter(prefix="/api/v1/execute", tags=["Execute"])


@router.post("/run", response_model=BaseResponse[CodeRunResponse])
async def run_code(payload: CodeRunRequest, user: User = Depends(get_current_user)):
    """Chạy thử từ Monaco Editor, không ghi Submission hoặc đổi trạng thái phòng.

    Body gồm question_id, language và code_content. JWT đi trong Bearer token.
    data.results chứa chi tiết testcase công khai; lỗi chấm như FAIL/TLE vẫn
    trả HTTP 200. Request không hợp lệ hoặc chưa xác thực được xử lý riêng.
    """
    # UUID lấy từ user đã xác thực; client không được tự chọn người sở hữu file code.
    # BaseResponse giữ cấu trúc success/message/data/... thống nhất với API khác.
    return BaseResponse(data=await execute.run_code(payload, user.id))


@router.post("/submit", response_model=BaseResponse[SubmissionResponse])
async def submit_code(payload: SubmissionCreateRequest, user: User = Depends(get_current_user)):
    """Nộp chính thức: body thêm room_id bên cạnh question_id, language, code_content.

    Service kiểm tra quyền trong phòng, chấm tất cả testcase và lưu lịch sử.
    Response chỉ chứa Submission tổng hợp, không chứa input/output testcase ẩn.
    """
    # Router không tự commit hay broadcast để tránh tách rời transaction chốt trận.
    return BaseResponse(data=await execute.submit_code(payload, user.id))
