
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.models import MatchmakingEntry, Room, RoomPlayer, User
from app.services.room_service import get_active_room

GAME_MODE_RANKED = "RANKED_1V1"
OPEN_ROOM_STATUSES = ("WAITING", "PLAYING")
READY_COUNTDOWN_SECONDS = 5


def match_found_message(room_code: str, opponent: User) -> dict:
    """Payload sự kiện MATCH_FOUND (AC 4.3), gửi cho một người chơi với `opponent` là đối thủ của họ."""
    return {
        "event": "MATCH_FOUND",
        "data": {
            "room_code": room_code,
            "opponent": {
                "username": opponent.username,
                "avatar_url": opponent.avatar_url,
                "rating": opponent.rating,
            },
            "countdown_seconds": READY_COUNTDOWN_SECONDS,
        },
    }


async def join_queue(db: AsyncSession, user: User) -> MatchmakingEntry:
    """AC 1: vào hàng đợi Ranked. Chỉ tạo entry, không ghép cặp."""
    user_id = user.id

    # AC 1.1: không được đang ở trong phòng chưa kết thúc
    active_room = await get_active_room(db, user_id)
    if active_room is not None:
        raise ConflictException(
            "Bạn đang ở trong một phòng đang hoạt động",
            details={"room_id": str(active_room.id), "room_code": active_room.code},
        )

    # AC 1.2: Partial Unique Index uq_matchmaking_searching_user chặn bấm trùng
    entry = MatchmakingEntry(user_id=user_id, game_mode=GAME_MODE_RANKED, status="searching")
    db.add(entry)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BadRequestException(
            "Bạn đang trong hàng đợi tìm trận, vui lòng không gửi yêu cầu trùng lặp"
        )

    await db.refresh(entry)
    return entry


async def _open_matched_entry(db: AsyncSession, user_id: UUID) -> MatchmakingEntry | None:
    """Entry đã matched mà phòng vẫn còn WAITING/PLAYING."""
    stmt = (
        select(MatchmakingEntry)
        .join(Room, Room.id == MatchmakingEntry.room_id)
        .where(
            MatchmakingEntry.user_id == user_id,
            MatchmakingEntry.status == "matched",
            Room.status.in_(OPEN_ROOM_STATUSES),
        )
        .order_by(MatchmakingEntry.matched_at.desc())
    )
    return (await db.execute(stmt)).scalars().first()


async def cancel_queue(db: AsyncSession, user_id: UUID) -> MatchmakingEntry:
    """AC 2: hủy lượt tìm trận đang searching."""
    # FOR UPDATE: nếu worker đang ghép đúng entry này thì chờ worker xong rồi đọc lại,
    # lúc đó entry đã 'matched' và không còn khớp điều kiện 'searching'.
    entry = (
        await db.execute(
            select(MatchmakingEntry)
            .where(
                MatchmakingEntry.user_id == user_id,
                MatchmakingEntry.status == "searching",
            )
            .with_for_update()
        )
    ).scalars().first()

    if entry is None:
        if await _open_matched_entry(db, user_id) is not None:
            raise BadRequestException("Trận đấu đã được ghép, không thể hủy hàng đợi")
        raise NotFoundException("Không tìm thấy hàng đợi tìm trận đang hoạt động")

    entry.status = "cancelled"
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_queue_status(db: AsyncSession, user_id: UUID) -> MatchmakingEntry | None:
    """Entry searching/matched mới nhất của user. matched chỉ tính khi phòng còn WAITING/PLAYING."""
    entry = (
        await db.execute(
            select(MatchmakingEntry)
            .where(
                MatchmakingEntry.user_id == user_id,
                MatchmakingEntry.status.in_(("searching", "matched")),
            )
            .order_by(MatchmakingEntry.created_at.desc())
        )
    ).scalars().first()
    if entry is None:
        return None
    if entry.status == "matched":
        room = await db.get(Room, entry.room_id) if entry.room_id else None
        if room is None or room.status not in OPEN_ROOM_STATUSES:
            return None
    return entry


async def opponent_for(db: AsyncSession, entry: MatchmakingEntry, user_id: UUID) -> User | None:
    """Đối thủ trong phòng của entry, None nếu chưa ghép."""
    if entry.room_id is None:
        return None
    stmt = (
        select(User)
        .join(RoomPlayer, RoomPlayer.user_id == User.id)
        .where(RoomPlayer.room_id == entry.room_id, RoomPlayer.user_id != user_id)
    )
    return (await db.execute(stmt)).scalars().first()
