import asyncio
from uuid import UUID

from fastapi import WebSocket


class MatchmakingSocketManager:
    def __init__(self):
        # user_id -> WebSocket (mỗi user 1 kết nối)
        self.user_sockets: dict[UUID, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: UUID) -> None:
        """Chấp nhận kết nối; nếu user đã có kết nối cũ thì thay thế và đóng kết nối cũ (4001)."""
        await websocket.accept()
        async with self._lock:
            old = self.user_sockets.get(user_id)
            self.user_sockets[user_id] = websocket
        if old is not None:
            try:
                await old.close(code=4001, reason="Replaced by new connection")
            except Exception:
                pass

    async def disconnect(self, user_id: UUID, websocket: WebSocket) -> bool:
        """Chỉ gỡ nếu `websocket` đúng là kết nối hiện tại của user."""
        async with self._lock:
            if self.user_sockets.get(user_id) is not websocket:
                return False
            del self.user_sockets[user_id]
            return True

    async def send_to_user(self, user_id: UUID, message: dict) -> bool:
        """Gửi JSON cho user. True nếu gửi được, False nếu user không online hoặc lỗi gửi."""
        websocket = self.user_sockets.get(user_id)
        if websocket is None:
            return False
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            return False


matchmaking_manager = MatchmakingSocketManager()
