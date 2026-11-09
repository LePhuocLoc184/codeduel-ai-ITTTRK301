from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Room, RoomPlayer, User
from app.schemas.response import BaseResponse
from app.schemas.users import (
    LeaderboardItemResponse,
    RankBadge,
    RecentMatchItem,
    TokenResponse,
    UserBaseResponse,
    UserLoginRequest,
    UserProfileDashboardResponse,
    UserRegisterSchema,
    UserRole,
    UserUpdateSchema
)
from app.services import users as user_service


router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"]
)

# =============================== REGION ===============================


@router.get("/me", response_model=BaseResponse[UserProfileDashboardResponse])
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """API GET /api/v1/users/me: Trả về thông tin User hiện tại + WinRate % +
    History."""
    dashboard = await user_service.get_profile_dashboard(db, current_user)
    return BaseResponse(data=dashboard)
# =============================== END REGION ===============================


# =============================== REGION ===============================

@router.put("/me", response_model=BaseResponse[UserBaseResponse])
async def update_me(
    payload: UserUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """API PUT /api/v1/users/me: Cập nhật avatar_url, đổi mật khẩu."""
    updated_user = await user_service.update_profile(
        db, current_user, payload
    )
    return BaseResponse(
        message="Cập nhật thành công",
        data=UserBaseResponse.model_validate(updated_user),
    )
# =============================== END REGION ===============================


# =============================== XEM THÔNG TIN TÀI KHOẢN ===============================

@router.get("/profile", response_model=BaseResponse[UserProfileDashboardResponse])
async def profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    dashboard = await user_service.get_profile_dashboard(db, current_user)
    return BaseResponse(data=dashboard)
# =============================== END REGION ===============================


# =============================== XEM BẢNG XẾP HẠNG ===============================
@router.get("/leaderboard", response_model=BaseResponse[list[LeaderboardItemResponse]])
async def leaderboard(db: AsyncSession = Depends(get_db)):
    """API GET /api/v1/users/leaderboard: Query Top 100 User có rating cao
    nhất."""
    items = await user_service.get_leaderboard(db, limit=100)
    return BaseResponse(data=items)
# =============================== XEM BẢNG XẾP HẠNG ===============================


@router.get("/{user_id}/history", response_model=BaseResponse[list[RecentMatchItem]])
async def get_user_history(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """API GET /api/v1/users/{user_id}/history: Trả về danh sách 10 phòng đấu
    gần nhất của user."""
    history = await user_service.get_user_history(db, user_id)
    return BaseResponse(data=history)
