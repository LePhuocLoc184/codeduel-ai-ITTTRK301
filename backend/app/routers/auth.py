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
)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
_email_adapter = TypeAdapter(EmailStr)


def rank_badge_for(rating: int) -> RankBadge:
    if rating >= 1700:
        return RankBadge.DIAMOND
    if rating >= 1500:
        return RankBadge.GOLD
    if rating >= 1300:
        return RankBadge.SILVER
    return RankBadge.BRONZE


def win_rate_for(wins: int, rated_games: int) -> float:
    if rated_games <= 0:
        return 0.0
    return round((wins / rated_games) * 100, 2)


def _normalize_email(value: str) -> str:
    try:
        return str(_email_adapter.validate_python(value.strip().lower()))
    except ValidationError:
        raise BadRequestException("Email không hợp lệ")


def _normalize_username(value: str) -> str:
    username = value.strip()
    if not 3 <= len(username) <= 50:
        raise BadRequestException("Username phải từ 3 đến 50 ký tự")
    if not all(char.isalnum() or char == "_" for char in username):
        raise BadRequestException("Username chỉ gồm chữ, số và dấu gạch dưới")
    return username


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserBaseResponse.model_validate(user),
    )


async def _find_duplicate(db: AsyncSession, username: str, email: str) -> User | None:
    stmt = select(User).where(
        (func.lower(User.username) == username.lower()) | (func.lower(User.email) == email)
    )
    return (await db.execute(stmt)).scalars().first()


def _is_decisive_win(player: RoomPlayer, mates: list[RoomPlayer]) -> bool:
    if any(mate.elo_change != 0 for mate in mates):
        return player.elo_change > 0
    if len(mates) < 2:
        return False
    top_score = max(mate.score for mate in mates)
    leaders = [mate for mate in mates if mate.score == top_score]
    return len(leaders) == 1 and leaders[0].user_id == player.user_id


async def _recent_matches(db: AsyncSession, user_id: UUID) -> list[RecentMatchItem]:
    rooms = (
        await db.execute(
            select(Room)
            .join(RoomPlayer, RoomPlayer.room_id == Room.id)
            .where(RoomPlayer.user_id == user_id, Room.status == "FINISHED")
            .order_by(Room.finished_at.desc())
            .limit(10)
        )
    ).scalars().all()
    if not rooms:
        return []

    room_ids = [room.id for room in rooms]
    players = (
        await db.execute(select(RoomPlayer).where(RoomPlayer.room_id.in_(room_ids)))
    ).scalars().all()
    grouped: dict[UUID, list[RoomPlayer]] = {}
    for player in players:
        grouped.setdefault(player.room_id, []).append(player)

    items: list[RecentMatchItem] = []
    for room in rooms:
        mates = grouped.get(room.id, [])
        me = next((player for player in mates if player.user_id == user_id), None)
        if me is None:
            continue
        items.append(RecentMatchItem(
            room_id=room.id,
            game_mode=room.game_mode,
            is_win=_is_decisive_win(me, mates),
            elo_change=me.elo_change,
            finished_at=room.finished_at,
        ))
    return items


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=BaseResponse[TokenResponse])
async def register(payload: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
    username = _normalize_username(payload.username)
    email = _normalize_email(payload.email)
    if await _find_duplicate(db, username, email):
        raise ConflictException("Username hoặc email đã tồn tại")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        role="user",
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictException("Username hoặc email đã tồn tại")
    await db.refresh(user)
    return BaseResponse(message="Đăng ký thành công", data=_token_response(user))


@router.post("/login", response_model=BaseResponse[TokenResponse])
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    user = (
        await db.execute(select(User).where(func.lower(User.email) == email))
    ).scalars().first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedException("Email hoặc mật khẩu không đúng")
    return BaseResponse(message="Đăng nhập thành công", data=_token_response(user))


@router.get("/me", response_model=BaseResponse[UserBaseResponse])
async def me(current_user: User = Depends(get_current_user)):
    return BaseResponse(data=UserBaseResponse.model_validate(current_user))


@router.get("/profile", response_model=BaseResponse[UserProfileDashboardResponse])
async def profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    recent = await _recent_matches(db, current_user.id)
    dashboard = UserProfileDashboardResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        avatar_url=current_user.avatar_url,
        rating=current_user.rating,
        created_at=current_user.created_at,
        rated_games=current_user.rated_games,
        wins=current_user.wins,
        win_rate=win_rate_for(current_user.wins, current_user.rated_games),
        rank_badge=rank_badge_for(current_user.rating),
        recent_matches=recent,
    )
    return BaseResponse(data=dashboard)


@router.get("/leaderboard", response_model=BaseResponse[list[LeaderboardItemResponse]])
async def leaderboard(db: AsyncSession = Depends(get_db)):
    users = (
        await db.execute(
            select(User).order_by(User.rating.desc(), User.wins.desc(), User.username.asc()).limit(100)
        )
    ).scalars().all()
    items = [
        LeaderboardItemResponse(
            rank=index,
            id=user.id,
            avatar_url=user.avatar_url,
            username=user.username,
            rating=user.rating,
            rated_games=user.rated_games,
            wins=user.wins,
            win_rate=win_rate_for(user.wins, user.rated_games),
            rank_badge=rank_badge_for(user.rating),
        )
        for index, user in enumerate(users, start=1)
    ]
    return BaseResponse(data=items)
