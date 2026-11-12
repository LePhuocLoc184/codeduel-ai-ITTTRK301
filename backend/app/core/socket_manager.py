import asyncio
from uuid import UUID
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # State Connection Pool (Lưu trữ kết nối: room_code -> {user_id: WebSocket})
        self.active_rooms: dict[str, dict[UUID, WebSocket]] = {}

        # Quản lý trạng thái Sẵn sàng của người chơi trong phòng
        self.ready_players: dict[str, set[UUID]] = {}

        # Quản lý trạng thái phòng tránh kích hoạt đếm ngược nhiều lần
        # Các trạng thái: 'WAITING', 'COUNTING', 'PLAYING'
        self.room_states: dict[str, str] = {}

        # Đảm bảo Thread-Safety / Async Safe khi thao tác với Dictionary
        self._lock = asyncio.Lock()

        # Lưu reference của các background task (đếm ngược) để tránh bị Garbage Collect
        self._tasks: set[asyncio.Task] = set()

    async def connect(self, websocket: WebSocket, room_code: str, user_id: UUID) -> bool:
        """
        Quản lý kết nối vào Arena và xử lý reconnect/ghi đè.
        """
        async with self._lock:
            # Khởi tạo phòng nếu chưa tồn tại
            if room_code not in self.active_rooms:
                self.active_rooms[room_code] = {}
                self.ready_players[room_code] = set()
                self.room_states[room_code] = 'WAITING'

            # Giới hạn phòng tối đa 2 người chơi (Mode 1v1)
            # Chỉ từ chối khi phòng đã đủ 2 người VÀ người mới không thuộc phòng
            if len(self.active_rooms[room_code]) >= 2 and user_id not in self.active_rooms[room_code]:
                await websocket.accept()
                await websocket.close(code=4000, reason="Room is full")
                return False

            # Lấy kết nối cũ (nếu cùng user_id vào lại từ tab/thiết bị khác)
            old_ws = self.active_rooms[room_code].get(user_id)

            # Chấp nhận bắt tay (handshake) và ghi đè kết nối mới vào pool
            await websocket.accept()
            self.active_rooms[room_code][user_id] = websocket

        # Đóng kết nối cũ SAU khi đã thay thế trong pool.
        # Route của socket cũ sẽ gọi disconnect(..., old_ws) nhưng sẽ bị bỏ qua
        # vì old_ws không còn là socket hiện tại.
        if old_ws is not None:
            try:
                await old_ws.close(code=4001, reason="Replaced by new connection")
            except Exception:
                pass

        return True

    async def disconnect(
        self,
        room_code: str,
        user_id: UUID,
        websocket: WebSocket | None = None,
    ) -> str | None:
        """
        Gỡ client khỏi phòng, tự xóa phòng trong RAM nếu không còn ai.

        Trả về trạng thái RAM của phòng ngay TRƯỚC khi gỡ ('WAITING' / 'COUNTING' /
        'PLAYING' / ...), hoặc None nếu không gỡ được gì (đã bị gỡ rồi, hoặc socket này
        không còn là kết nối hiện tại của user). Route dùng giá trị này để quyết định
        có hủy phòng hay không.
        """
        async with self._lock:
            room = self.active_rooms.get(room_code)
            if room is None or user_id not in room:
                return None

            if websocket is not None and room[user_id] is not websocket:
                return None

            previous_state = self.room_states.get(room_code, "WAITING")
            del room[user_id]

            # Có người thoát giữa lúc đếm ngược thì hủy đếm ngược
            if previous_state == "COUNTING":
                self.room_states[room_code] = "WAITING"

            if len(room) == 0:
                del self.active_rooms[room_code]
                self.room_states.pop(room_code, None)
                self.countdown_ids.pop(room_code, None)

            return previous_state

    async def broadcast(self, room_code: str, message_dict: dict):
        """
        Truyền phát tín hiệu Event song song tới tất cả người chơi trong phòng.
        """
        if room_code not in self.active_rooms:
            return

        # Lấy danh sách để tránh lỗi Dictionary changed size during iteration
        connections = list(self.active_rooms[room_code].items())

        async def _send(uid: UUID, conn: WebSocket):
            try:
                await conn.send_json(message_dict)
            except Exception:
                # Truyền đúng `conn` để không xóã nhầm kết nối mới của cùng user
                await self.disconnect(room_code, uid, conn)

        # Dùng asyncio.gather để gửi song song, không bị nghẽn nếu client khác treo
        tasks = [_send(uid, conn) for uid, conn in connections]
        if tasks:
            await asyncio.gather(*tasks)

    async def send_personal(self, room_code: str, user_id: UUID, message_dict: dict):
        """
        Gửi tín hiệu riêng cho một user cụ thể (VD: Kết quả Compile Error cá nhân).
        """
        connection = self.active_rooms.get(room_code, {}).get(user_id)
        if connection is None:
            return

        try:
            await connection.send_json(message_dict)
        except Exception:
            await self.disconnect(room_code, user_id, connection)

    async def begin_countdown(self, room_code: str) -> bool:
        async with self._lock:
            if self.room_states.get(room_code) != "WAITING":
                return None
            self.room_states[room_code] = "COUNTING"
            self._cid_counter += 1
            self.countdown_ids[room_code] = self._cid_counter
            return self._cid_counter

    async def cancel_countdown(self, room_code: str) -> None:
        async with self._lock:
            if self.room_states.get(room_code) == "COUNTING":
                self.room_states[room_code] = "WAITING"

    def is_counting(self, room_code: str, cid: int) -> bool:
        return (
            self.room_states.get(room_code) == "COUNTING"
            and self.countdown_ids.get(room_code) == cid
        )
    
    def connected_count(self, room_code: str) -> int:
        """Số người đang kết nối WebSocket trong phòng."""
        return len(self.active_rooms.get(room_code, {}))
    
    
    def track_task(self, task: asyncio.Task) -> None:
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def confirm_match_start(self, room_code: str) -> bool:
        """Chốt COUNTING -> PLAYING. Trả về False nếu countdown đã bị hủy."""
        async with self._lock:
            if self.room_states.get(room_code) != "COUNTING":
                return False
            self.room_states[room_code] = "PLAYING"
            return True

    async def sync_status(self, room_code: str, status: str) -> None:
        """Đồng bộ state trong RAM với status phòng trên DB, không ghi đè countdown."""
        async with self._lock:
            if room_code not in self.room_states:
                return
            if status == "PLAYING":
                self.room_states[room_code] = "PLAYING"
            elif status == "WAITING" and self.room_states.get(room_code) != "COUNTING":
                self.room_states[room_code] = "WAITING"

    async def handle_player_ready(self, room_code: str, user_id: UUID):
        """
        Xử lý sự kiện Ready & Kích hoạt đếm ngược.
        """
        async with self._lock:
            if room_code in self.ready_players:
                self.ready_players[room_code].add(user_id)

                # Kiểm tra đúng trạng thái WAITING và đủ 2 người mới đếm ngược
                if len(self.ready_players[room_code]) == 2 and self.room_states.get(room_code) == 'WAITING':
                    self.room_states[room_code] = 'COUNTING'

                    # Lưu task vào _tasks set để tránh bị Garbage Collect
                    task = asyncio.create_task(self._trigger_countdown(room_code))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)

    async def _trigger_countdown(self, room_code: str):
        """
        Tiến trình ngầm đếm ngược bắt đầu trận (Có cơ chế ngắt an toàn).
        """
        await self.broadcast(room_code, {"event": "PLAYER_READY", "status": "All players ready"})

        for i in range(3, 0, -1):
            # Kiểm tra nếu state thay đổi (có người out) thì hủy countdown
            if self.room_states.get(room_code) != 'COUNTING':
                await self.broadcast(room_code, {"event": "COUNTDOWN_ABORTED", "message": "Player disconnected. Waiting..."})
                return

            await self.broadcast(room_code, {"event": "COUNTDOWN", "value": i})
            await asyncio.sleep(1)

        # Kiểm tra lần cuối trước khi chốt vào trận
        if self.room_states.get(room_code) == 'COUNTING':
            self.room_states[room_code] = 'PLAYING'
            await self.broadcast(room_code, {"event": "COUNTDOWN_START", "message": "Match Started!"})
        else:
            await self.broadcast(room_code, {"event": "COUNTDOWN_ABORTED", "message": "Player disconnected. Waiting..."})

    async def update_progress(self, room_code: str, user_id: UUID, passed_testcases: int, total_testcases: int):
        """
        Cập nhật Tiến độ Real-time / Thanh máu người chơi.
        """
        await self.broadcast(room_code, {
            "event": "PROGRESS_UPDATE",
            "user_id": str(user_id),
            "passed": passed_testcases,
            "total": total_testcases,
            "progress_percent": round((passed_testcases / total_testcases) * 100, 2) if total_testcases > 0 else 0
        })


# Khởi tạo Pool Connection duy nhất (Singleton Pattern)
manager = ConnectionManager()