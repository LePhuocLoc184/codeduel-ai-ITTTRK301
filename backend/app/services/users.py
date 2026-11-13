from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, UnauthorizedException
from app.core.security import hash_password, verify_password
from app.models import Room, RoomPlayer, User
from app.schemas.users import (
    LeaderboardItemResponse,
    RecentMatchItem,
    UserProfileDashboardResponse,
    UserRole,
    UserUpdateSchema,
)
from app.utils import game_helpers


async def get_user_history(
    db: AsyncSession, user_id: UUID
) -> list[RecentMatchItem]:
    """Lấy danh sách 10 phòng đấu gần nhất của một user bất kỳ."""
    user_room_ids = (
        select(RoomPlayer.room_id)
        .where(RoomPlayer.user_id == user_id)
        .scalar_subquery()
    )

    rooms = (
        await db.execute(
            select(Room)
            .where(Room.id.in_(user_room_ids), Room.status == "FINISHED")
            .order_by(Room.finished_at.desc())
            .limit(10)
        )
    ).scalars().all()

    if not rooms:
        return []

    room_ids = [room.id for room in rooms]
    players = (
        await db.execute(
            select(RoomPlayer).where(RoomPlayer.room_id.in_(room_ids))
        )
    ).scalars().all()

    grouped: dict[UUID, list[RoomPlayer]] = {}
    for player in players:
        grouped.setdefault(player.room_id, []).append(player)

    items: list[RecentMatchItem] = []
    for room in rooms:
        mates = grouped.get(room.id, [])
        me = next(
            (player for player in mates if player.user_id == user_id), None
        )
        if me is None:
            continue
        items.append(
            RecentMatchItem(
                room_id=room.id,
                game_mode=room.game_mode,
                # Dùng winner_id chính thức, kể cả trận Custom có elo_change = 0.
                # Phòng cũ chưa có winner_id vẫn dùng cách suy luận từ Elo/score
                # của game_helpers để giữ khả năng hiển thị lịch sử trước migration.
                is_win=(room.winner_id == user_id if room.winner_id is not None
                        else game_helpers._is_decisive_win(me, mates)),
                elo_change=me.elo_change,
                finished_at=room.finished_at,
            )
        )
    return items


async def get_profile_dashboard(
    db: AsyncSession, current_user: User
) -> UserProfileDashboardResponse:
    """Tổng hợp thông tin Dashboard / Profile cho user hiện tại."""
    recent = await get_user_history(db, current_user.id)
    return UserProfileDashboardResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=UserRole(current_user.role),
        avatar_url=current_user.avatar_url,
        rating=current_user.rating,
        created_at=current_user.created_at,
        rated_games=current_user.rated_games,
        wins=current_user.wins,
        win_rate=game_helpers.win_rate_for(
            current_user.wins, current_user.rated_games
        ),
        rank_badge=game_helpers.rank_badge_for(current_user.rating),
        recent_matches=recent,
    )


async def update_profile(
    db: AsyncSession, current_user: User, payload: UserUpdateSchema
) -> User:
    """Cập nhật avatar_url hoặc đổi mật khẩu."""
    updated = False

    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
        updated = True

    if payload.new_password:
        if not payload.old_password:
            raise BadRequestException(
                "Vui lòng nhập mật khẩu hiện tại để đổi mật khẩu mới"
            )
        if not verify_password(
            payload.old_password, current_user.password_hash
        ):
            raise UnauthorizedException("Mật khẩu hiện tại không đúng")
        current_user.password_hash = hash_password(payload.new_password)
        updated = True

    if updated:
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)

    return current_user


async def get_leaderboard(
    db: AsyncSession, limit: int = 100
) -> list[LeaderboardItemResponse]:
    """Query Top User có rating cao nhất."""
    users = (
        await db.execute(
            select(User)
            .order_by(
                User.rating.desc(), User.wins.desc(), User.username.asc()
            )
            .limit(limit)
        )
    ).scalars().all()

    return [
        LeaderboardItemResponse(
            rank=index,
            id=user.id,
            avatar_url=user.avatar_url,
            username=user.username,
            rating=user.rating,
            rated_games=user.rated_games,
            wins=user.wins,
            win_rate=game_helpers.win_rate_for(
                user.wins, user.rated_games
            ),
            rank_badge=game_helpers.rank_badge_for(user.rating),
        )
        for index, user in enumerate(users, start=1)
    ]
    
    
