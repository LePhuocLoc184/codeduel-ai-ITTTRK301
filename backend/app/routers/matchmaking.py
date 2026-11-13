"""
Router chỉ lo HTTP/WebSocket: nhận request, gọi service, trả response. Không chứa nghiệp vụ.
"""
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.core.matchmaking_socket import matchmaking_manager
from app.db.database import get_db
from app.dependencies.auth import get_current_user, get_user_from_token
from app.models import Room, User
from app.schemas.matchmaking_entries import MatchmakingJoinRequest
from app.schemas.response import BaseResponse
from app.schemas.rooms import GameMode
from app.services.matchmaking import (
    cancel_queue,
    get_queue_status,
    join_queue,
    match_found_message,
    opponent_for,
)

router = APIRouter(prefix="/api/v1/matchmaking", tags=["Matchmaking"])


@router.post("/join", response_model=BaseResponse[dict])
async def join_matchmaking(
    payload: MatchmakingJoinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AC 1: vào hàng đợi tìm trận Ranked."""
    if payload.game_mode != GameMode.RANKED_1V1:
        raise BadRequestException("Hàng đợi chỉ hỗ trợ chế độ RANKED_1V1")
    entry = await join_queue(db, current_user)
    return BaseResponse(
        message="Đã vào hàng đợi tìm trận",
        data={"entry_id": str(entry.id), "status": entry.status},
    )


@router.delete("/cancel", response_model=BaseResponse[dict])
async def cancel_matchmaking(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AC 2: hủy tìm trận."""
    entry = await cancel_queue(db, current_user.id)
    return BaseResponse(
        message="Đã hủy tìm trận",
        data={"entry_id": str(entry.id), "status": entry.status},
    )


@router.get("/status", response_model=BaseResponse[dict])
async def matchmaking_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dự phòng khi client mất WebSocket (không có trong AC)."""
    entry = await get_queue_status(db, current_user.id)
    if entry is None:
        return BaseResponse(data={"status": "idle"})

    data = {"entry_id": str(entry.id), "status": entry.status}
    if entry.status == "matched":
        room = await db.get(Room, entry.room_id) if entry.room_id else None
        opponent = await opponent_for(db, entry, current_user.id)
        if room is not None and opponent is not None:
            data.update(match_found_message(room.code, opponent)["data"])
    return BaseResponse(data=data)


@router.websocket("/ws")
async def matchmaking_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Kênh nhận MATCH_FOUND (AC 4.3). URL: /api/v1/matchmaking/ws?token=<jwt>"""
    user = await get_user_from_token(token, db)
    if user is None:
        await websocket.accept()
        await websocket.close(code=4003, reason="Invalid token")
        return

    user_id = user.id
    await matchmaking_manager.connect(websocket, user_id)
    try:
        entry = await get_queue_status(db, user_id)
        if entry is not None and entry.status == "matched":
            room = await db.get(Room, entry.room_id) if entry.room_id else None
            opponent = await opponent_for(db, entry, user_id)
            if room is not None and opponent is not None:
                await matchmaking_manager.send_to_user(
                    user_id, match_found_message(room.code, opponent)
                )
        # Chỉ để phát hiện client ngắt kết nối
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await matchmaking_manager.disconnect(user_id, websocket)
