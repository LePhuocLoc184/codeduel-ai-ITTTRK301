from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models import MatchmakingEntry, Room, User
from app.schemas.matchmaking_entries import MatchmakingJoinRequest
from app.schemas.response import BaseResponse
from app.schemas.rooms import GameMode
from app.services.matchmaking import cancel_queue, join_queue, opponent_for
from app.services.room_service import get_active_room

router = APIRouter(prefix="/api/v1/matchmaking", tags=["Matchmaking"])


async def _open_ranked_entry(db: AsyncSession, user_id: UUID) -> MatchmakingEntry | None:
    stmt = (
        select(MatchmakingEntry)
        .join(Room, Room.id == MatchmakingEntry.room_id)
        .where(
            MatchmakingEntry.user_id == user_id,
            MatchmakingEntry.status == "matched",
            Room.status.in_(("WAITING", "PLAYING")),
        )
        .order_by(MatchmakingEntry.matched_at.desc())
    )
    return (await db.execute(stmt)).scalars().first()


async def _payload(db: AsyncSession, entry: MatchmakingEntry, user_id: UUID) -> dict:
    room = await db.get(Room, entry.room_id) if entry.room_id else None
    opponent = await opponent_for(db, entry, user_id)
    return {
        "entry_id": str(entry.id),
        "status": entry.status,
        "game_mode": entry.game_mode,
        "room_id": str(entry.room_id) if entry.room_id else None,
        "room_code": room.code if room else None,
        "room_status": room.status if room else None,
        "opponent": None if opponent is None else {
            "id": str(opponent.id),
            "username": opponent.username,
            "rating": opponent.rating,
            "avatar_url": opponent.avatar_url,
        },
    }


@router.post("/join", response_model=BaseResponse[dict])
async def join_matchmaking(
    payload: MatchmakingJoinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.game_mode != GameMode.RANKED_1V1:
        raise BadRequestException("Hàng đợi chỉ hỗ trợ chế độ RANKED_1V1")

    active_room = await get_active_room(db, current_user.id)
    if active_room is not None:
        entry = await _open_ranked_entry(db, current_user.id)
        if entry is None or entry.room_id != active_room.id:
            raise ConflictException(
                "Bạn đang ở trong một phòng đang hoạt động",
                details={"room_id": str(active_room.id), "room_code": active_room.code},
            )
        return BaseResponse(message="Đã ghép trận", data=await _payload(db, entry, current_user.id))

    entry = await join_queue(db, current_user, payload.game_mode.value)
    message = "Đã ghép trận" if entry.status == "matched" else "Đang tìm đối thủ"
    return BaseResponse(message=message, data=await _payload(db, entry, current_user.id))


@router.post("/cancel", response_model=BaseResponse[dict])
async def cancel_matchmaking(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await cancel_queue(db, current_user.id)
    if entry is None:
        return BaseResponse(message="Bạn không có lượt tìm trận nào", data={"status": "idle"})
    return BaseResponse(message="Đã hủy tìm trận", data=await _payload(db, entry, current_user.id))


@router.get("/status", response_model=BaseResponse[dict])
async def matchmaking_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = (
        await db.execute(
            select(MatchmakingEntry)
            .where(
                MatchmakingEntry.user_id == current_user.id,
                MatchmakingEntry.status.in_(("searching", "matched")),
            )
            .order_by(MatchmakingEntry.created_at.desc())
        )
    ).scalars().first()
    if entry is None:
        return BaseResponse(data={"status": "idle"})
    if entry.status == "matched":
        room = await db.get(Room, entry.room_id) if entry.room_id else None
        if room is None or room.status not in {"WAITING", "PLAYING"}:
            return BaseResponse(data={"status": "idle"})
    return BaseResponse(data=await _payload(db, entry, current_user.id))
