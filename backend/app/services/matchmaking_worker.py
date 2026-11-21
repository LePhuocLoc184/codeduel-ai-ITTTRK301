"""
Background worker ghép trận (AC 3 + AC 4). Chạy định kỳ mỗi 2 giây.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.matchmaking_socket import matchmaking_manager
from app.db.database import AsyncSessionLocal
from app.models import MatchmakingEntry, Question, Room, RoomPlayer, User
from app.services.matchmaking import GAME_MODE_RANKED, match_found_message
from app.services.room_service import generate_unique_room_code

logger = logging.getLogger(__name__)

TICK_SECONDS = 2               # Chu kỳ quét hàng đợi (2 giây/lần)
BASE_RATING_GAP = 150          # Chênh lệch Rating tối đa khi chờ < 30 giây
EXPANDED_RATING_GAP = 300      # Chênh lệch Rating tối đa khi chờ >= 30 giây
EXPAND_AFTER_SECONDS = 30      # Mốc thời gian mở rộng biên độ ghép cặp
READY_COUNTDOWN_SECONDS = 5    # Thời gian đếm ngược chuẩn bị vào trận (AC 4.3)

Candidate = tuple[MatchmakingEntry, User]


def _ensure_utc(dt: datetime) -> datetime:
    """Đảm bảo đối tượng datetime luôn có múi giờ UTC để tính toán không bị lệch."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def allowed_gap(wait_seconds: float) -> int:
    """AC 3.2: Trả về khoảng cách Rating cho phép (150 nếu chờ < 30s, 300 nếu chờ >= 30s)."""
    if wait_seconds >= EXPAND_AFTER_SECONDS:
        return EXPANDED_RATING_GAP
    return BASE_RATING_GAP


def find_pairs(candidates: list[Candidate], now: datetime) -> list[tuple[Candidate, Candidate]]:
    """
    AC 3.2 - Ghép cặp danh sách người chơi đang tìm trận (đã sắp xếp theo created_at tăng dần).
    Ưu tiên người chờ lâu nhất trước, kiểm tra cùng chế độ chơi và độ lệch Rating.
    """
    now_utc = _ensure_utc(now)
    paired_indices: set[int] = set()
    pairs: list[tuple[Candidate, Candidate]] = []

    for i, (entry1, user1) in enumerate(candidates):
        # Bỏ qua nếu người chơi này đã được ghép cặp ở vòng lặp trước
        if i in paired_indices:
            continue

        # Tính thời gian đã chờ và biên độ Rating cho phép của người thứ nhất
        wait_seconds = max(0.0, (now_utc - _ensure_utc(entry1.created_at)).total_seconds())
        gap = allowed_gap(wait_seconds)

        for j in range(i + 1, len(candidates)):
            # Bỏ qua nếu ứng viên thứ hai đã được ghép cặp
            if j in paired_indices:
                continue

            entry2, user2 = candidates[j]
            # Đảm bảo không tự ghép với chính mình và phải cùng chế độ chơi
            if entry1.user_id == entry2.user_id:
                continue
            if entry1.game_mode != entry2.game_mode:
                continue

            # Kiểm tra chênh lệch Rating: |Rating_1 - Rating_2| <= gap
            if abs(user1.rating - user2.rating) <= gap:
                paired_indices.add(i)
                paired_indices.add(j)
                pairs.append(((entry1, user1), (entry2, user2)))
                break

    return pairs


async def fetch_searching(db: AsyncSession) -> list[Candidate]:
    """
    AC 3.2: Truy vấn danh sách (MatchmakingEntry, User) đang ở trạng thái 'searching',
    sắp xếp theo thời gian vào hàng đợi tăng dần và khóa bản ghi để tránh xung đột với lệnh hủy.
    """
    stmt = (
        select(MatchmakingEntry, User)
        .join(User, User.id == MatchmakingEntry.user_id)
        .where(MatchmakingEntry.status == "searching")
        .order_by(MatchmakingEntry.created_at.asc())
        .with_for_update(skip_locked=True, of=MatchmakingEntry)
    )
    rows = (await db.execute(stmt)).all()
    return [(entry, user) for entry, user in rows]


async def _pick_random_question(db: AsyncSession) -> Question:
    """Bốc ngẫu nhiên 1 câu hỏi trong cơ sở dữ liệu cho phòng đấu."""
    stmt = select(Question).order_by(func.random()).limit(1)
    question = (await db.execute(stmt)).scalars().first()
    if question is None:
        raise RuntimeError("Không tìm thấy câu hỏi nào trong cơ sở dữ liệu để tạo phòng đấu")
    return question


async def create_ranked_room(db: AsyncSession, first: Candidate, second: Candidate) -> Room:
    """
    AC 4.1 + 4.2: Tự động tạo phòng đấu RANKED_1V1, gán câu hỏi ngẫu nhiên,
    thêm 2 người chơi vào phòng và cập nhật trạng thái hàng đợi thành 'matched'.
    """
    entry1, user1 = first
    entry2, user2 = second

    question = await _pick_random_question(db)
    now = datetime.now(timezone.utc)

    # Người vào hàng đợi sớm hơn sẽ được chọn làm chủ phòng (host)
    t1 = _ensure_utc(entry1.created_at)
    t2 = _ensure_utc(entry2.created_at)
    host_id = user1.id if t1 <= t2 else user2.id

    # Khởi tạo phòng mới với chế độ RANKED_1V1 và gán question_id
    room = Room(
        code=await generate_unique_room_code(db),
        host_id=host_id,
        game_mode=GAME_MODE_RANKED,
        status="WAITING",
        question_id=question.id,
    )
    db.add(room)
    await db.flush()

    # Thêm 2 người chơi vào phòng với trạng thái sẵn sàng (is_ready=True)
    db.add_all([
        RoomPlayer(room_id=room.id, user_id=user1.id, is_ready=True),
        RoomPlayer(room_id=room.id, user_id=user2.id, is_ready=True),
    ])

    # Cập nhật trạng thái của 2 bản ghi tìm trận sang 'matched' và gán room_id
    for entry in (entry1, entry2):
        entry.status = "matched"
        entry.room_id = room.id
        entry.matched_at = now

    await db.flush()
    return room


async def notify_match_found(room: Room, first: Candidate, second: Candidate) -> None:
    """
    AC 4.3: Bắn sự kiện WebSocket 'MATCH_FOUND' kèm room_code và thông tin đối thủ
    tới cả 2 người chơi để phía client tự động chuyển màn hình vào Arena.
    """
    _, user1 = first
    _, user2 = second

    await asyncio.gather(
        matchmaking_manager.send_to_user(user1.id, match_found_message(room.code, user2)),
        matchmaking_manager.send_to_user(user2.id, match_found_message(room.code, user1)),
    )


async def run_matchmaking_tick() -> int:
    """
    Thực thi một chu kỳ quét hàng đợi: lấy danh sách chờ, ghép cặp, tạo phòng,
    lưu vào cơ sở dữ liệu rồi mới gửi thông báo WebSocket cho 2 phía.
    """
    now = datetime.now(timezone.utc)
    matched_results: list[tuple[Room, Candidate, Candidate]] = []

    async with AsyncSessionLocal() as db:
        candidates = await fetch_searching(db)
        if len(candidates) < 2:
            return 0

        pairs = find_pairs(candidates, now)
        if not pairs:
            return 0

        for first, second in pairs:
            room = await create_ranked_room(db, first, second)
            matched_results.append((room, first, second))

        # Lưu toàn bộ thay đổi vào DB trước khi bắn sự kiện WebSocket
        await db.commit()

    # Gửi thông báo MATCH_FOUND sau khi đã commit thành công
    for room, first, second in matched_results:
        await notify_match_found(room, first, second)

    return len(matched_results)


async def matchmaking_worker() -> None:
    """
    AC 3.1: Vòng lặp chạy ngầm liên tục mỗi 2 giây để quét và ghép trận tự động.
    """
    while True:
        try:
            await run_matchmaking_tick()
        except asyncio.CancelledError:
            # Cho phép hủy task an toàn khi tắt server
            raise
        except Exception:
            logger.exception("Lỗi phát sinh trong chu kỳ quét ghép trận (matchmaking worker tick)")
        await asyncio.sleep(TICK_SECONDS)