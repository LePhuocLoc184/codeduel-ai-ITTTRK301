import asyncio
from uuid import UUID
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_rooms: dict[str, dict[UUID, WebSocket]] = {}
        self.room_states: dict[str, str] = {}
        self.countdown_ids: dict[str, int] = {}
        self._cid_counter = 0
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()

    async def connect(self, websocket: WebSocket, room_code: str, user_id: UUID) -> bool:
        """
        Quản lý kết nối vào Arena và xử lý reconnect/ghi đè.
        """
        async with self._lock:
            # Khởi tạo phòng nếu chưa tồn tại
            if room_code not in self.active_rooms:
                self.active_rooms[room_code] = {}
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
    async def close_room(
        self,
        room_code: str,
        message_dict: dict | None = None,
        code: int = 4002,
        reason: str = "Room closed",
    ) -> None:
        """Xóa phòng khỏi RAM, báo (nếu có) rồi đóng kết nối của những người còn lại."""
        async with self._lock:
            room = self.active_rooms.pop(room_code, {})
            self.room_states.pop(room_code, None)
            self.countdown_ids.pop(room_code, None)
            connections = list(room.values())

        async def _close(conn: WebSocket):
            try:
                if message_dict is not None:
                    await conn.send_json(message_dict)
                await conn.close(code=code, reason=reason)
            except Exception:
                pass

        await asyncio.gather(*(_close(conn) for conn in connections))
        
        
    async def broadcast(self, room_code: str, message_dict: dict):
        """Gửi song song tới tất cả người chơi trong phòng."""
        room = self.active_rooms.get(room_code)
        if not room:
            return

        connections = list(room.values())

        async def _send(conn: WebSocket):
            try:
                await conn.send_json(message_dict)
            except Exception:
                # Không gọi disconnect ở đây: route của socket này sẽ tự dọn
                # khi nhận WebSocketDisconnect.
                pass

        await asyncio.gather(*(_send(conn) for conn in connections))

    async def send_personal(self, room_code: str, user_id: UUID, message_dict: dict):
        """Gửi tin nhắn riêng cho một user."""
        connection = self.active_rooms.get(room_code, {}).get(user_id)
        if connection is None:
            return
        try:
            await connection.send_json(message_dict)
        except Exception:
            pass

    async def begin_countdown(self, room_code: str) -> int | None:
        async with self._lock:
            if self.room_states.get(room_code) != "WAITING":
                return None
            self.room_states[room_code] = "COUNTING"
            self._cid_counter += 1
            self.countdown_ids[room_code] = self._cid_counter
            return self._cid_counter

    async def cancel_countdown(self, room_code: str, cid: int) -> None:
        async with self._lock:
            if self.is_counting(room_code, cid):
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

    async def confirm_match_start(self, room_code: str, cid: int) -> bool:
        async with self._lock:
            if not self.is_counting(room_code, cid):
                return False
            self.room_states[room_code] = "PLAYING"
            return True

    async def sync_status(self, room_code: str, status: str) -> None:
        """Đồng bộ state trong RAM với status phòng trên DB, không ghi đè countdown."""
        async with self._lock:
            if room_code not in self.room_states:
                return
            if status in ("PLAYING", "FINISHED"):
                self.room_states[room_code] = status
            elif status == "WAITING" and self.room_states.get(room_code) != "COUNTING":
                self.room_states[room_code] = "WAITING"


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