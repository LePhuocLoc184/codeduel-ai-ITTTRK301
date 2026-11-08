import asyncio
from uuid import UUID
from typing import Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # State Connection Pool (Lưu trữ kết nối: room_code -> {user_id: WebSocket})
        self.active_rooms: Dict[str, Dict[UUID, WebSocket]] = {}
        
        # Quản lý trạng thái Sẵn sàng của người chơi trong phòng
        self.ready_players: Dict[str, Set[UUID]] = {}
        
        # Quản lý trạng thái phòng tránh kích hoạt đếm ngược nhiều lần
        # Các trạng thái: 'WAITING', 'COUNTING', 'PLAYING'
        self.room_states: Dict[str, str] = {}
        
        # Đảm bảo Thread-Safety / Async Safe khi thao tác với Dictionary
        self._lock = asyncio.Lock()
        
        # Lưu reference của các background task (đếm ngược) để tránh bị Garbage Collect
        self._tasks: Set[asyncio.Task] = set()

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

            # Đóng kết nối cũ nếu cùng user_id vào lại (mở tab/thiết bị khác)
            if user_id in self.active_rooms[room_code]:
                old_ws = self.active_rooms[room_code][user_id]
                try:
                    await old_ws.close(code=4001, reason="Replaced by new connection")
                except Exception:
                    pass

            # Giới hạn phòng tối đa 2 người chơi (Mode 1v1)
            # Chỉ từ chối khi phòng đã đủ 2 người VÀ người mới không thuộc phòng
            if len(self.active_rooms[room_code]) >= 2 and user_id not in self.active_rooms[room_code]:
                await websocket.accept()
                await websocket.close(code=4000, reason="Room is full")
                return False

            # Chấp nhận bắt tay (handshake)
            await websocket.accept()
            self.active_rooms[room_code][user_id] = websocket
            
        # Phát tín hiệu JOIN_ROOM (bắn ra ngoài lock để không block hệ thống)
        await self.broadcast(room_code, {
            "event": "JOIN_ROOM",
            "user_id": str(user_id),
            "message": "A new player has joined the arena."
        })
        
        return True

    async def disconnect(self, room_code: str, user_id: UUID):
        """
        Ngắt kết nối, giải phóng Pool và xóa phòng an toàn.
        """
        async with self._lock:
            if room_code in self.active_rooms:
                # Gỡ bỏ websocket của người chơi
                if user_id in self.active_rooms[room_code]:
                    del self.active_rooms[room_code][user_id]
                
                # Gỡ trạng thái ready nếu có
                if room_code in self.ready_players and user_id in self.ready_players[room_code]:
                    self.ready_players[room_code].remove(user_id)

                # Hủy tiến trình đếm ngược nếu có người thoát giữa chừng
                if self.room_states.get(room_code) == 'COUNTING':
                    self.room_states[room_code] = 'WAITING'
                
                # Tránh Memory Leak: Dọn dẹp key hoàn toàn nếu phòng trống
                if len(self.active_rooms[room_code]) == 0:
                    del self.active_rooms[room_code]
                    if room_code in self.ready_players:
                        del self.ready_players[room_code]
                    if room_code in self.room_states:
                        del self.room_states[room_code]

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
                # Gọi disconnect an toàn vì broadcast KHÔNG giữ _lock (tránh Deadlock)
                await self.disconnect(room_code, uid)

        # Dùng asyncio.gather để gửi song song, không bị nghẽn nếu client khác treo
        tasks = [_send(uid, conn) for uid, conn in connections]
        if tasks:
            await asyncio.gather(*tasks)

    async def send_personal(self, room_code: str, user_id: UUID, message_dict: dict):
        """
        Gửi tín hiệu riêng cho một user cụ thể (VD: Kết quả Compile Error cá nhân).
        """
        if room_code in self.active_rooms and user_id in self.active_rooms[room_code]:
            connection = self.active_rooms[room_code][user_id]
            try:
                await connection.send_json(message_dict)
            except Exception:
                # Nếu gửi lỗi (do client đã ngắt kết nối đột ngột), tiến hành dọn dẹp an toàn
                await self.disconnect(room_code, user_id)

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