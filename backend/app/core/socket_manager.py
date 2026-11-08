import asyncio
from uuid import UUID
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        # Cấu trúc lưu trữ kết nối: room_code -> {user_id: WebSocket}
        self.active_rooms: Dict[str, Dict[UUID, WebSocket]] = {}
        
        # Cấu trúc: room_code -> tập hợp (Set) chứa user_id của những người đã sẵn sàng
        self.ready_players: Dict[str, Set[UUID]] = {}
        
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room_code: str, user_id: UUID) -> bool:
        """
        Quản lý kết nối và giới hạn phòng đấu (AC 2.1 & FR-2.3)
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

    async def disconnect(self, room_code: str, user_id: UUID):
        """
        Quản lý ngắt kết nối và giải phóng bộ nhớ (AC 2.2)
        """
        async with self._lock:
            if room_code in self.active_rooms:
                if user_id in self.active_rooms[room_code]:
                    del self.active_rooms[room_code][user_id]
                
                if room_code in self.ready_players and user_id in self.ready_players[room_code]:
                    self.ready_players[room_code].remove(user_id)
                
                if len(self.active_rooms[room_code]) == 0:
                    del self.active_rooms[room_code]
                    if room_code in self.ready_players:
                        del self.ready_players[room_code]

    async def broadcast(self, room_code: str, message_dict: dict):
        """
        Truyền phát tin nhắn JSON tới toàn bộ người chơi trong phòng (AC 3.1 & FR-2.3)
        Sử dụng cho: PLAYER_TYPING, COUNTDOWN_START, GAME_OVER
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
        Gửi tin nhắn riêng tư cho 1 người chơi cụ thể (AC 3.2)
        """
        if room_code in self.active_rooms and user_id in self.active_rooms[room_code]:
            connection = self.active_rooms[room_code][user_id]
            try:
                await connection.send_json(message_dict)
            except (WebSocketDisconnect, RuntimeError):
                await self.disconnect(room_code, user_id)

    async def handle_player_ready(self, room_code: str, user_id: UUID):
        """
        FR-2.3: Xử lý sự kiện PLAYER_READY.
        Nếu cả 2 người cùng sẵn sàng, kích hoạt COUNTDOWN_START.
        """
        async with self._lock:
            if room_code in self.ready_players:
                self.ready_players[room_code].add(user_id)
                
                if len(self.ready_players[room_code]) == 2:
                    asyncio.create_task(self._trigger_countdown(room_code))

    async def _trigger_countdown(self, room_code: str):
        """
        Tiến trình ngầm đếm ngược 3-2-1 theo chuẩn FR-2.3 User Journey Bước 3
        """
        await self.broadcast(room_code, {"event": "PLAYER_READY", "status": "All players ready"})
        
        for i in range(3, 0, -1):
            await self.broadcast(room_code, {"event": "COUNTDOWN", "value": i})
            await asyncio.sleep(1)
            
        await self.broadcast(room_code, {"event": "COUNTDOWN_START", "message": "Match Started!"})

manager = ConnectionManager()