import asyncio
from uuid import UUID
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        # State Connection Pool (Theo Mục 4 Sơ đồ Kiến trúc)
        # Lưu trữ kết nối: room_code -> {user_id: WebSocket}
        self.active_rooms: Dict[str, Dict[UUID, WebSocket]] = {}
        
        # Quản lý trạng thái Sẵn sàng của người chơi trong phòng
        self.ready_players: Dict[str, Set[UUID]] = {}
        
        # Đảm bảo Thread-Safety / Async Safe
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room_code: str, user_id: UUID) -> bool:
        """
        Quản lý kết nối vào Arena.
        """
        async with self._lock:
            if room_code not in self.active_rooms:
                self.active_rooms[room_code] = {}
                self.ready_players[room_code] = set()

            # Giới hạn phòng tối đa 2 người chơi (Mode 1v1)
            if len(self.active_rooms[room_code]) >= 2:
                await websocket.accept()
                await websocket.close(code=4000, reason="Room is full")
                return False

            await websocket.accept()
            self.active_rooms[room_code][user_id] = websocket
            
        # Phát tín hiệu JOIN_ROOM
        await self.broadcast(room_code, {
            "event": "JOIN_ROOM",
            "user_id": str(user_id),
            "message": "A new player has joined the arena."
        })
        
        return True

    async def disconnect(self, room_code: str, user_id: UUID):
        """
        Ngắt kết nối và giải phóng Pool.
        """
        async with self._lock:
            if room_code in self.active_rooms:
                if user_id in self.active_rooms[room_code]:
                    del self.active_rooms[room_code][user_id]
                
                if room_code in self.ready_players and user_id in self.ready_players[room_code]:
                    self.ready_players[room_code].remove(user_id)
                
                # Tránh Memory Leak
                if len(self.active_rooms[room_code]) == 0:
                    del self.active_rooms[room_code]
                    if room_code in self.ready_players:
                        del self.ready_players[room_code]

    async def broadcast(self, room_code: str, message_dict: dict):
        """
        Truyền phát tín hiệu Event chung (Typing, Game Over, Error).
        """
        if room_code not in self.active_rooms:
            return

        connections = list(self.active_rooms[room_code].items())
        
        for uid, connection in connections:
            try:
                await connection.send_json(message_dict)
            except (WebSocketDisconnect, RuntimeError):
                await self.disconnect(room_code, uid)

    async def send_personal(self, message_dict: dict, room_code: str, user_id: UUID):
        """
        Gửi tín hiệu riêng (VD: Kết quả Compile Error cá nhân).
        """
        if room_code in self.active_rooms and user_id in self.active_rooms[room_code]:
            connection = self.active_rooms[room_code][user_id]
            try:
                await connection.send_json(message_dict)
            except (WebSocketDisconnect, RuntimeError):
                await self.disconnect(room_code, user_id)

    async def handle_player_ready(self, room_code: str, user_id: UUID):
        """
        Xử lý sự kiện Ready & Kích hoạt đếm ngược.
        """
        async with self._lock:
            if room_code in self.ready_players:
                self.ready_players[room_code].add(user_id)
                
                if len(self.ready_players[room_code]) == 2:
                    asyncio.create_task(self._trigger_countdown(room_code))

    async def _trigger_countdown(self, room_code: str):
        """
        Tiến trình ngầm đếm ngược bắt đầu trận.
        """
        await self.broadcast(room_code, {"event": "PLAYER_READY", "status": "All players ready"})
        for i in range(3, 0, -1):
            await self.broadcast(room_code, {"event": "COUNTDOWN", "value": i})
            await asyncio.sleep(1)
        await self.broadcast(room_code, {"event": "COUNTDOWN_START", "message": "Match Started!"})

    async def update_progress(self, room_code: str, user_id: UUID, passed_testcases: int, total_testcases: int):
        """
        HÀM MỚI BỔ SUNG: Cập nhật "Thanh máu / Tiến độ Real-time" 
        (Dựa theo Mục 2.2 và Sơ đồ Kiến trúc Luồng 3 - Progress Event)
        """
        await self.broadcast(room_code, {
            "event": "PROGRESS_UPDATE",
            "user_id": str(user_id),
            "passed": passed_testcases,
            "total": total_testcases,
            "progress_percent": round((passed_testcases / total_testcases) * 100, 2) if total_testcases > 0 else 0
        })

manager = ConnectionManager()

async def connect(self, websocket: WebSocket, room_code: str, user_id: UUID) -> bool:
    """
    Chấp nhận kết nối WebSocket và thêm client vào phòng đấu.
    Trả về True nếu kết nối thành công, False nếu phòng đã đầy.
    """
    async with self._lock:
        if room_code not in self.active_rooms:
            self.active_rooms[room_code] = {}
            self.ready_players[room_code] = set()

        if len(self.active_rooms[room_code]) >= 2:
            await websocket.accept()
            await websocket.close(code=4000, reason="Room is full")
            return False

        await websocket.accept()
        self.active_rooms[room_code][user_id] = websocket
        
    await self.broadcast(room_code, {
        "event": "JOIN_ROOM",
        "user_id": str(user_id),
        "message": "A new player has joined the arena."
    })
    
    return True