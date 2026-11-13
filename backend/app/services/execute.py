"""Nối API chạy thử/nộp bài với Runner, database và WebSocket.

Run: đọc testcase công khai -> chấm -> trả kết quả, không ghi DB.
Submit: kiểm tra phòng -> chấm toàn bộ testcase -> khóa phòng và kiểm tra lại
-> lưu Submission -> chốt trận nếu thắng -> commit -> gửi GAME_OVER.

Runner chỉ chấm code. Service này quyết định chọn testcase nào, ghi dữ liệu
gì và lúc nào được công nhận người thắng.
"""
import asyncio
import logging
from uuid import UUID

from sqlalchemy import select, func
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import BadRequestException, NotFoundException, ForbiddenException
from app.core.socket_manager import manager
from app.db.database import AsyncSessionLocal
from app.models import Question, Room, RoomPlayer, User, Submission
from app.schemas.submissions import CodeRunRequest, CodeRunResponse, SubmissionCreateRequest, SubmissionResponse
from app.services.elo import calculate_elo
from app.services.judge import judge_code

logger = logging.getLogger(__name__)


async def _question_data(db, question_id: UUID, public_only: bool) -> tuple:
    """Trả về (testcases, thời gian tối đa mỗi case theo giây, RAM theo MB).

    public_only=True dành cho Run; False dành cho Submit.
    Hàm chỉ đọc Question, không cập nhật bài toán hay phòng đấu.
    """
    question = await db.get(Question, question_id)
    if question is None:
        raise NotFoundException("Không tìm thấy bài toán")
    # Kiểm tra dữ liệu JSON trong DB trước khi đưa vào Runner:
    # mỗi testcase phải là dictionary, input và expected_output phải là chuỗi.
    if not isinstance(question.test_cases, list) or any(
        not isinstance(case, dict) or not isinstance(case.get("input"), str)
        or not isinstance(case.get("expected_output"), str) for case in question.test_cases
    ):
        raise BadRequestException("Testcase của bài toán không đúng định dạng")
    # Run chỉ nhận is_hidden đúng bằng False; thiếu cờ thì không coi là public.
    # Submit lấy tất cả. dict(case) tạo bản sao để không sửa trực tiếp JSON của ORM.
    cases = [dict(case) for case in question.test_cases
             if not public_only or case.get("is_hidden") is False]
    if not cases:
        # Không được coi 0/0 testcase là PASS rồi công nhận chiến thắng.
        raise BadRequestException("Bài toán chưa có testcase phù hợp để chấm")
    if question.time_limit <= 0 or question.memory_limit <= 0:
        raise BadRequestException("Giới hạn thời gian/bộ nhớ của bài toán không hợp lệ")
    return cases, question.time_limit, question.memory_limit


async def run_code(payload: CodeRunRequest, user_id: UUID) -> CodeRunResponse:
    """Chạy thử để hiển thị Console: có file tạm nhưng không có bản ghi Submission."""
    # Session chỉ đọc: tuyệt đối không thêm Submission hay cập nhật Room.
    async with AsyncSessionLocal() as db:
        cases, seconds, megabytes = await _question_data(db, payload.question_id, True)
    # Đóng session đọc trước khi chấm. Chạy công việc đồng bộ trong thread pool
    # để vòng lặp async của server vẫn tiếp nhận request và tin nhắn WebSocket.
    result = await run_in_threadpool(judge_code, payload.code_content, payload.language,
                                   user_id, cases, seconds, megabytes)
    # results chỉ chứa testcase công khai; lỗi compile không có kết quả chạy case.
    # Trạng thái chấm FAIL/TLE/... vẫn là dữ liệu của HTTP 200, không phải lỗi API.
    return CodeRunResponse(
        status=result["status"], results=result["results"],
        compile_error_message=result["error_message"] if result["status"] == "COMPILE_ERROR" else None,
        error_message=result["error_message"],
    )


async def _validate_room(db, payload: SubmissionCreateRequest, user_id: UUID, lock=False):
    """Kiểm tra phòng, bài toán và quyền nộp; lock=True dùng trước lúc ghi DB.

    Trả 404 khi phòng không tồn tại, 400 khi trạng thái/bài toán không hợp lệ,
    403 khi người đang đăng nhập không phải thành viên phòng.
    """
    query = select(Room).where(Room.id == payload.room_id)
    if lock:
        # FOR UPDATE giữ khóa dòng đến lúc transaction commit/rollback.
        # populate_existing nạp lại dữ liệu, không dùng trạng thái PLAYING cũ
        # còn trong session nếu đối thủ đã kết thúc trận trong lúc mình chấm.
        query = query.with_for_update().execution_options(populate_existing=True)
    room = await db.scalar(query)
    if room is None:
        raise NotFoundException("Không tìm thấy phòng đấu")
    if room.status != "PLAYING" or room.rating_applied:
        # rating_applied là chốt chặn thứ hai để không tính kết quả trận nhiều lần.
        raise BadRequestException("Phòng chưa bắt đầu hoặc trận đấu đã kết thúc")
    if room.question_id != payload.question_id:
        # Không cho nộp một bài khác dễ hơn để giành chiến thắng trong phòng này.
        raise BadRequestException("Bài toán không thuộc trận đấu hiện tại")
    member = await db.scalar(select(RoomPlayer.id).where(
        RoomPlayer.room_id == room.id, RoomPlayer.user_id == user_id))
    if member is None:
        raise ForbiddenException("Bạn không tham gia phòng đấu này")
    return room


async def _finish_game(db, room: Room, winner_id: UUID) -> dict:
    """Ghi kết quả trận và tạo payload GAME_OVER, chưa commit hoặc gửi Socket.

    Caller phải đã khóa phòng và xác nhận bài nộp PASS toàn bộ testcase.
    Tất cả thay đổi ở đây thuộc transaction đang lưu Submission của caller.
    """
    # Khóa các dòng người chơi trước khi sửa elo_change của trận hiện tại.
    players = list((await db.scalars(select(RoomPlayer).where(
        RoomPlayer.room_id == room.id).with_for_update())).all())
    if len(players) != 2:
        raise BadRequestException("Trận đấu cần đúng hai người chơi")
    # Khóa user theo thứ tự cố định để tránh deadlock giữa các transaction.
    users = list((await db.scalars(select(User).where(
        User.id.in_([player.user_id for player in players]))
        .order_by(User.id).with_for_update())).all())
    winner = next(user for user in users if user.id == winner_id)
    loser = next(user for user in users if user.id != winner_id)
    winner_delta, loser_delta = (0, 0)
    # Custom không thay đổi rating; chỉ Ranked gọi công thức Elo.
    if room.game_mode == "RANKED_1V1":
        winner_delta, loser_delta = calculate_elo(winner.rating, loser.rating, 1)
        winner.rating += winner_delta
        loser.rating += loser_delta
    # Hành vi hiện tại: thống kê wins/rated_games tăng ở cả Ranked và Custom.
    # Riêng rating và elo_change của Custom giữ mức thay đổi bằng 0.
    winner.wins += 1
    winner.rated_games += 1
    loser.rated_games += 1
    for player in players:
        # Lưu delta của riêng trận này để xem lịch sử, không lưu tổng rating ở đây.
        player.elo_change = winner_delta if player.user_id == winner_id else loser_delta
    room.status = "FINISHED"
    room.winner_id = winner_id
    room.rating_applied = True
    # Lấy giờ thực tế từ PostgreSQL tại lúc chốt trận. clock_timestamp() không
    # cố định ở thời điểm bắt đầu transaction như CURRENT_TIMESTAMP.
    room.finished_at = await db.scalar(select(func.clock_timestamp()))
    # completion_time là số giây từ lúc trận bắt đầu đến khi chốt thắng,
    # khác execution_time là thời gian chạy các testcase của một bài nộp.
    duration = max(0.0, (room.finished_at - room.started_at).total_seconds()) if room.started_at else 0.0
    # Chuyển UUID/datetime sang chuỗi để send_json có thể gửi trực tiếp.
    return {
        "room_id": str(room.id), "winner_id": str(winner_id),
        "winner_username": winner.username, "loser_id": str(loser.id),
        "winner_elo_change": winner_delta, "loser_elo_change": loser_delta,
        "elo_change": {str(winner_id): winner_delta, str(loser.id): loser_delta},
        "finished_at": room.finished_at.isoformat(), "completion_time": duration,
    }


async def _broadcast_game_over(room_code: str, event: dict) -> None:
    """Đồng bộ trạng thái Socket trong tiến trình hiện tại rồi gửi kết quả trận."""
    # Phát ngay sau commit; kết nối chậm không giữ HTTP request vô hạn.
    await manager.sync_status(room_code, "FINISHED")
    try:
        # 0.1 giây là thời hạn CHỜ GỬI, không bảo đảm client nhận trong 100 ms.
        # Hết hạn thì wait_for hủy lần gửi đang chờ; DB đã commit không bị rollback.
        await asyncio.wait_for(manager.broadcast(room_code, {"event": "GAME_OVER", "data": event}), timeout=0.1)
    except TimeoutError:
        logger.warning("GAME_OVER delivery exceeded 100 ms for room %s", room_code)


async def submit_code(payload: SubmissionCreateRequest, user_id: UUID) -> SubmissionResponse:
    """Nộp chính thức bằng UUID của user đã xác thực, không nhận user_id từ body.

    Có hai transaction ngắn tách bởi bước chấm code. Transaction đầu chỉ đọc;
    transaction sau lưu lịch sử và kết quả trận một cách đồng bộ.
    """
    async with AsyncSessionLocal() as db:
        async with db.begin():
            # Bước 1: từ chối request sai trước khi tốn tài nguyên chạy chương trình.
            await _validate_room(db, payload, user_id)
            cases, seconds, megabytes = await _question_data(db, payload.question_id, False)

        # Không giữ khóa DB trong lúc compile/chạy code; socket vẫn xử lý bình thường.
        result = await run_in_threadpool(judge_code, payload.code_content, payload.language,
                                       user_id, cases, seconds, megabytes)
        event = None
        async with db.begin():
            # Bước 2: khóa và kiểm tra lại sau khi chấm. Nếu đối thủ đã chốt thắng,
            # request này trả 400 và không tạo Submission, dù đã chạy xong testcase.
            # Hai lượt nộp cùng PASS: transaction chốt phòng trước được tính thắng.
            room = await _validate_room(db, payload, user_id, lock=True)
            room_code = room.code
            error = result["error_message"]
            # Không trả stderr runtime của hidden testcase (code có thể in lại input).
            if result["status"] == "RUNTIME_ERROR":
                error = "Chương trình gặp lỗi khi thực thi"
            # Lưu một bản ghi cho bài nộp hợp lệ, kể cả khi compile/chạy bị lỗi.
            # Không đưa input, expected_output hoặc actual_output của hidden case
            # vào SubmissionResponse; client chỉ nhận số lượng và số đo tổng hợp.
            submission = Submission(
                room_id=room.id, user_id=user_id, question_id=payload.question_id,
                code_content=payload.code_content, language=payload.language.value,
                status=result["status"], passed_test_cases=result["passed_test_cases"],
                total_test_cases=result["total_test_cases"], execution_time=result["execution_time"],
                memory_used=result["memory_used"], error_message=error,
            )
            db.add(submission)
            player = await db.scalar(select(RoomPlayer).where(
                RoomPlayer.room_id == room.id, RoomPlayer.user_id == user_id))
            # Giữ thành tích tốt nhất trong trận; bài nộp tệ hơn không làm giảm score.
            player.score = max(player.score, result["passed_test_cases"])
            # Cần đồng thời PASS, có testcase và đạt đủ tất cả case mới chốt thắng.
            if (result["status"] == "PASS" and result["total_test_cases"] > 0
                    and result["passed_test_cases"] == result["total_test_cases"]):
                event = await _finish_game(db, room, user_id)
            # flush gửi INSERT/UPDATE xuống DB và nhận id/created_at của Submission,
            # nhưng chưa commit. Lỗi flush hoặc tạo response vẫn rollback transaction.
            await db.flush()
            response = SubmissionResponse.model_validate(submission)
        # Thoát db.begin() bình thường mới commit; có exception thì rollback cả
        # Submission, score, Room và User. Chỉ sau commit mới báo thắng qua Socket.
        if event is not None:
            await _broadcast_game_over(room_code, event)
        return response
