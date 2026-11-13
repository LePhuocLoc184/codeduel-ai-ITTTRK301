from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.response import BaseResponse
from app.schemas.users import TokenResponse, UserLoginRequest, UserRegisterSchema
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=BaseResponse[TokenResponse],
)
async def register(
    payload: UserRegisterSchema, db: AsyncSession = Depends(get_db)
):
    """API Đăng ký tài khoản mới."""
    token_data = await auth_service.register_user(db, payload)
    return BaseResponse(message="Đăng ký thành công", data=token_data)


@router.post("/login", response_model=BaseResponse[TokenResponse])
async def login(
    payload: UserLoginRequest, db: AsyncSession = Depends(get_db)
):
    """API Đăng nhập lấy Access Token."""
    token_data = await auth_service.authenticate_user(db, payload)
    return BaseResponse(message="Đăng nhập thành công", data=token_data)
