from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MatchmakingEntry, Room, RoomPlayer, User
from app.services.room_service import generate_unique_room_code

ELO_BASE_WINDOW = 200
ELO_EXPAND_EVERY_SECONDS = 15
ELO_EXPAND_STEP = 100
ELO_MAX_WINDOW = 800


def elo_window(created_at: datetime, now: datetime) -> int:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    elapsed = max(0.0, (now - created_at).total_seconds())
    steps = int(elapsed // ELO_EXPAND_EVERY_SECONDS)
    return min(ELO_MAX_WINDOW, ELO_BASE_WINDOW + steps * ELO_EXPAND_STEP)


async def _searching_entry(db: AsyncSession, user_id: UUID) -> MatchmakingEntry | None:
    stmt = select(MatchmakingEntry).where(
        MatchmakingEntry.user_id == user_id,
        MatchmakingEntry.status == "searching",
    )
    return (await db.execute(stmt)).scalars().first()


async def _open_matched_entry(db: AsyncSession, user_id: UUID) -> MatchmakingEntry | None:
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


async def _create_ranked_room(
    db: AsyncSession,
    left: MatchmakingEntry,
    right: MatchmakingEntry,
) -> Room:
    now = datetime.now(timezone.utc)
    host_id = left.user_id if left.created_at <= right.created_at else right.user_id
    room = Room(
        code=await generate_unique_room_code(db),
        host_id=host_id,
        game_mode="RANKED_1V1",
        status="WAITING",
    )
    db.add(room)
    await db.flush()

    db.add_all([
        RoomPlayer(room_id=room.id, user_id=left.user_id, is_ready=False),
        RoomPlayer(room_id=room.id, user_id=right.user_id, is_ready=False),
    ])
    for entry in (left, right):
        entry.status = "matched"
        entry.room_id = room.id
        entry.matched_at = now
    await db.flush()
    return room


async def _try_pair(db: AsyncSession, entry: MatchmakingEntry, user: User) -> Room | None:
    locked = (
        await db.execute(
            select(MatchmakingEntry)
            .where(MatchmakingEntry.id == entry.id)
            .with_for_update()
        )
    ).scalars().first()
    if locked is None or locked.status != "searching":
        return None

    now = datetime.now(timezone.utc)
    my_window = elo_window(locked.created_at, now)
    candidates = (
        await db.execute(
            select(MatchmakingEntry, User)
            .join(User, User.id == MatchmakingEntry.user_id)
            .where(
                MatchmakingEntry.status == "searching",
                MatchmakingEntry.game_mode == locked.game_mode,
                MatchmakingEntry.user_id != user.id,
            )
            .order_by(MatchmakingEntry.created_at.asc())
            .with_for_update(skip_locked=True)
        )
    ).all()

    for candidate, opponent in candidates:
        allowed = max(my_window, elo_window(candidate.created_at, now))
        if abs(user.rating - opponent.rating) <= allowed:
            return await _create_ranked_room(db, locked, candidate)
    return None


async def join_queue(db: AsyncSession, user: User, game_mode: str) -> MatchmakingEntry:
    user_id = user.id
    open_match = await _open_matched_entry(db, user_id)
    if open_match is not None:
        return open_match

    entry = await _searching_entry(db, user_id)
    if entry is None:
        entry = MatchmakingEntry(user_id=user_id, game_mode=game_mode, status="searching")
        db.add(entry)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            existing = await _searching_entry(db, user_id)
            if existing is None:
                raise
            rebound = await db.get(User, user_id)
            if rebound is None:
                raise
            user = rebound
            entry = existing

    await _try_pair(db, entry, user)
    await db.commit()
    await db.refresh(entry)
    return entry


async def cancel_queue(db: AsyncSession, user_id: UUID) -> MatchmakingEntry | None:
    entry = await _searching_entry(db, user_id)
    if entry is None:
        return None
    entry.status = "cancelled"
    await db.commit()
    await db.refresh(entry)
    return entry


async def opponent_for(db: AsyncSession, entry: MatchmakingEntry, user_id: UUID) -> User | None:
    if entry.room_id is None:
        return None
    stmt = (
        select(User)
        .join(RoomPlayer, RoomPlayer.user_id == User.id)
        .where(
            RoomPlayer.room_id == entry.room_id,
            RoomPlayer.user_id != user_id,
        )
    )
    return (await db.execute(stmt)).scalars().first()
