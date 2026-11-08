import asyncio
from uuid import UUID
from typing import Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # State Connection Pool
        self.active_rooms: Dict[str, Dict[UUID, WebSocket]] = {}
        self.ready_players: Dict[str, Set[UUID]] = {}
        
        # Point 5: Quản lý trạng thái phòng tránh trigger countdown nhiều lần
        self.room_states: Dict[str, str] = {}  # 'WAITING', 'COUNTING', 'PLAYING'
        
        # Thread-Safety lock
        self._lock = asyncio.Lock()
        
        # Point 6: Lưu reference của các background task để tránh bị Garbage Collect
        self._tasks: Set[asyncio.Task] = set()

    async def connect(self, websocket: WebSocket, room_code: str, user_id: UUID) -> bool:
        """
        Quản lý kết nối vào Arena và xử lý reconnect/ghi đè.
        """
        async with self._lock:
            if room_code not in self.active_rooms:
                self.active_rooms[room_code] = {}
                self.ready_players[room_code] = set()
                self.room_states[room_code] = 'WAITING'

            # Point 4: Đóng kết nối cũ nếu cùng user_id vào lại bằng tab/thiết bị khác
            if user_id in self.active_rooms[room_code]:
                old_ws = self.active_rooms[room_code][user_id]
                try:
                    await old_ws.close(code=4001, reason="Replaced by new connection")
                except Exception:
                    pass

            # Point 4: Chỉ từ chối khi phòng đã có 2 người VÀ người mới không thuộc phòng
            if len(self.active_rooms[room_code]) >= 2 and user_id not in self.active_rooms[room_code]:
                await websocket.accept()
                await websocket.close(code=4000, reason="Room is full")
                return False

            await websocket.accept()
            self.active_rooms[room_code][user_id] = websocket
            
        # Tín hiệu bắn ra ngoài lock
        await self.broadcast(room_code, {
            "event": "JOIN_ROOM",
            "user_id": str(user_id),
            "message": "A new player has joined the arena."
        })
        
        return True

    async def disconnect(self, room_code: str, user_id: UUID):
        """
        Ngắt kết nối và giải phóng Pool. Xóa phòng an toàn.
        """
        async with self._lock:
            if room_code in self.active_rooms:
                if user_id in self.active_rooms[room_code]:
                    del self.active_rooms[room_code][user_id]
                
                if room_code in self.ready_players and user_id in self.ready_players[room_code]:
                    self.ready_players[room_code].remove(user_id)

                # Point 5: Hủy đếm ngược nếu có người thoát
                if self.room_states.get(room_code) == 'COUNTING':
                    self.room_states[room_code] = 'WAITING'
                
                # Dọn dẹp phòng trống
                if len(self.active_rooms[room_code]) == 0:
                    del self.active_rooms[room_code]
                    if room_code in self.ready_players:
                        del self.ready_players[room_code]
                    if room_code in self.room_states:
                        del self.room_states[room_code]

    async def broadcast(self, room_code: str, message_dict: dict):
        """
        Truyền phát tín hiệu Event song song tới tất cả user trong phòng.
        """
        if room_code not in self.active_rooms:
            return

        connections = list(self.active_rooms[room_code].items())
        
        # Point 7: Hàm bao bọc bắt mọi ngoại lệ rộng (Exception)
        async def _send(uid: UUID, conn: WebSocket):
            try:
                await conn.send_json(message_dict)
            except Exception:
                # Point 2: broadcast gọi disconnect ở đây là an toàn 
                # vì bản thân broadcast KHÔNG giữ _lock.
                await self.disconnect(room_code, uid)

        # Point 7: Dùng asyncio.gather để gửi song song, không bị chậm vì client khác treo
        tasks = [_send(uid, conn) for uid, conn in connections]
        if tasks:
            await asyncio.gather(*tasks)

    async def send_personal(self, message_dict: dict, room_code: str, user_id: UUID):
        """
        Gửi tín hiệu riêng cho một user cụ thể.
        """
        if room_code in self.active_rooms and user_id in self.active_rooms[room_code]:
            connection = self.active_rooms[room_code][user_id]
            try:
                await connection.send_json(message_dict)
            except Exception: # Bắt rộng giống broadcast
                await self.disconnect(room_code, user_id)

    async def handle_player_ready(self, room_code: str, user_id: UUID):
        """
        Xử lý sự kiện Ready. Tránh Trigger Countdown nhiều lần.
        """
        async with self._lock:
            if room_code in self.ready_players:
                self.ready_players[room_code].add(user_id)
                
                # Point 5: Kiểm tra đúng trạng thái WAITING mới bắt đầu đếm ngược
                if len(self.ready_players[room_code]) == 2 and self.room_states.get(room_code) == 'WAITING':
                    self.room_states[room_code] = 'COUNTING'
                    
                    # Point 6: Lưu task vào _tasks set để tránh bị GC
                    task = asyncio.create_task(self._trigger_countdown(room_code))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)

    async def _trigger_countdown(self, room_code: str):
        """
        Tiến trình ngầm đếm ngược bắt đầu trận.
        Có cơ chế an toàn ngắt giữa chừng nếu đối thủ disconnect.
        """
        await self.broadcast(room_code, {"event": "PLAYER_READY", "status": "All players ready"})
        
        for i in range(3, 0, -1):
            # Point 5: Kiểm tra nếu state thay đổi (có người out) thì hủy countdown
            if self.room_states.get(room_code) != 'COUNTING':
                await self.broadcast(room_code, {"event": "COUNTDOWN_ABORTED", "message": "Player disconnected. Waiting..."})
                return
                
            await self.broadcast(room_code, {"event": "COUNTDOWN", "value": i})
            await asyncio.sleep(1)
            
        # Kiểm tra cuối trước khi chốt vào trận
        if self.room_states.get(room_code) == 'COUNTING':
            self.room_states[room_code] = 'PLAYING'
            await self.broadcast(room_code, {"event": "COUNTDOWN_START", "message": "Match Started!"})

    async def update_progress(self, room_code: str, user_id: UUID, passed_testcases: int, total_testcases: int):
        """
        Cập nhật Tiến độ Real-time / Thanh tiến trình.
        """
        await self.broadcast(room_code, {
            "event": "PROGRESS_UPDATE",
            "user_id": str(user_id),
            "passed": passed_testcases,
            "total": total_testcases,
            "progress_percent": round((passed_testcases / total_testcases) * 100, 2) if total_testcases > 0 else 0
        })

# Khởi tạo Pool Connection duy nhất (Singleton)
manager = ConnectionManager()