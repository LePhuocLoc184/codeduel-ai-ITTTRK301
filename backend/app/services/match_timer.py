import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.socket_manager import manager
from app.db.database import AsyncSessionLocal
from app.models import Room, RoomPlayer, User
from app.services.elo import calculate_elo

logger = logging.getLogger(__name__)

MATCH_DURATION_SECONDS = 15 * 60
SYNC_INTERVAL_SECONDS = 10
SYNC_INTERVAL_LAST_MINUTE = 5
LAST_MINUTE_SECONDS = 60

RANKED_MODE = "RANKED_1V1"

_timers: dict[str, asyncio.Task] = {}


def start_match_timer(room_code: str, room_id: UUID, duration: float | None = None) -> None:
    """Bật timer cho phòng. Gọi ngay sau khi trận chuyển sang PLAYING. Gọi lần nữa cũng không tạo timer thứ hai."""
    current = _timers.get(room_code)
    if current is not None and not current.done():
        return

    task = asyncio.create_task(
        _run_timer(room_code, room_id, MATCH_DURATION_SECONDS if duration is None else duration)
    )
    _timers[room_code] = task

    def _cleanup(done: asyncio.Task) -> None:
        if _timers.get(room_code) is done:
            del _timers[room_code]

    task.add_done_callback(_cleanup)


def cancel_match_timer(room_code: str) -> bool:
    """
    AC 2.3: hủy timer của phòng. Gọi khi trận kết thúc sớm (có người PASS 100% hoặc bỏ cuộc).
    Trả về True nếu có timer đang chạy và đã bị hủy.
    """
    task = _timers.pop(room_code, None)
    if task is None or task.done():
        return False
    task.cancel()
    return True


async def _run_timer(room_code: str, room_id: UUID, duration: float) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + duration
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            await manager.broadcast(room_code, {
                "event": "TIME_SYNC",
                "data": {"remaining_seconds": int(remaining)},
            })
            interval = SYNC_INTERVAL_LAST_MINUTE if remaining <= LAST_MINUTE_SECONDS else SYNC_INTERVAL_SECONDS
            await asyncio.sleep(min(interval, remaining))
        await finish_by_timeout(room_code, room_id)
    except Exception:
        logger.exception("Match timer của phòng %s bị lỗi", room_code)


async def finish_by_timeout(room_code: str, room_id: UUID) -> None:
    """AC 3: hết giờ mà chưa ai thắng -> hòa."""
    if not hasattr(Room, "is_draw"):
        raise RuntimeError("Model Room chưa có cột is_draw, hãy thêm cột này trước")

    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        room = (
            await db.execute(select(Room).where(Room.id == room_id).with_for_update())
        ).scalars().first()
        # rating_applied là cờ chốt "kết quả trận đã được xử lý" của dự án, kiểm tra cùng status dưới khóa DB
        if room is None or room.status != "PLAYING" or room.rating_applied:
            return  # đã kết thúc bằng đường khác (có người thắng), không ghi đè

        players = (
            await db.execute(select(RoomPlayer).where(RoomPlayer.room_id == room.id))
        ).scalars().all()
        users: dict[UUID, User] = {}
        if players:
            rows = (
                await db.execute(
                    select(User)
                    .where(User.id.in_([player.user_id for player in players]))
                    .order_by(User.id)  # khóa theo thứ tự cố định để tránh deadlock
                    .with_for_update()
                )
            ).scalars().all()
            users = {user.id: user for user in rows}

        # AC 3.1
        room.status = "FINISHED"
        room.is_draw = True
        room.finished_at = now
        room.rating_applied = True  # giống trận thắng/thua: đánh dấu đã xử lý, kể cả phòng Custom

        # AC 3.2: Elo cho kết quả Hòa (Actual = 0.5). Chỉ phòng Ranked mới đổi điểm.
        deltas = {player.user_id: 0 for player in players}
        if room.game_mode == RANKED_MODE and len(players) == 2:
            first, second = players
            delta_first, delta_second = calculate_elo(
                users[first.user_id].rating, users[second.user_id].rating, 0.5
            )
            deltas[first.user_id] = delta_first
            deltas[second.user_id] = delta_second
            for player in players:
                users[player.user_id].rating += deltas[player.user_id]
        for player in players:
            player.elo_change = deltas[player.user_id]
            users[player.user_id].rated_games += 1

        summary = {
            "event": "MATCH_DRAW",
            "data": {
                "message": "Hết giờ, trận đấu hòa",
                "is_draw": True,
                "finished_at": now.isoformat(),
                "players": [
                    {
                        "user_id": str(player.user_id),
                        "username": users[player.user_id].username,
                        "rating": users[player.user_id].rating,
                        "elo_change": deltas[player.user_id],
                    }
                    for player in players
                ],
            },
        }
        await db.commit()

    await manager.sync_status(room_code, "FINISHED")
    await manager.broadcast(room_code, summary)


async def _fetch_playing_rooms() -> list[tuple[UUID, str, datetime | None]]:
    """Các phòng đang PLAYING mà kết quả chưa được xử lý (rating_applied còn False)."""
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Room.id, Room.code, Room.started_at).where(
                    Room.status == "PLAYING", Room.rating_applied.is_(False)
                )
            )
        ).all()
    return [(row[0], row[1], row[2]) for row in rows]


async def resume_match_timers() -> int:
    """
    Gọi MỘT LẦN khi server khởi động (trong lifespan): dựng lại timer cho các trận đang PLAYING
    mà server cũ bỏ dở. Thời gian còn lại tính từ rooms.started_at nên không bị "hồi lại" khi restart.
    - còn thời gian: chạy timer với phần còn lại
    - đã quá giờ trong lúc server tắt: chốt hòa ngay (đồng thời dọn các phòng PLAYING bị bỏ quên)
    Trả về số phòng đã khôi phục thành công. Lỗi của một phòng không làm hỏng phòng khác hay việc khởi động.
    """
    try:
        rooms = await _fetch_playing_rooms()
    except Exception:
        logger.exception("Không đọc được danh sách trận đang diễn ra để khôi phục timer")
        return 0

    now = datetime.now(timezone.utc)
    recovered = 0
    for room_id, room_code, started_at in rooms:
        try:
            if started_at is None:
                remaining = float(MATCH_DURATION_SECONDS)  # PLAYING mà thiếu started_at: coi như mới bắt đầu
            else:
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                remaining = MATCH_DURATION_SECONDS - (now - started_at).total_seconds()
            if remaining <= 0:
                await finish_by_timeout(room_code, room_id)
            else:
                start_match_timer(room_code, room_id, remaining)
            recovered += 1
        except Exception:
            logger.exception("Không khôi phục được timer của phòng %s", room_code)
    return recovered
