import asyncio
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.socket_manager import manager
from app.db.database import AsyncSessionLocal, get_db, get_db_ws
from app.dependencies.auth import get_current_user, get_user_from_token
from app.models import ProblemSet, Question, Room, RoomPlayer, User
from app.schemas.response import BaseResponse
from app.schemas.rooms import CustomRoomCreateRequest, JoinRoomRequest
from app.services.room_service import generate_unique_room_code, get_active_room

router = APIRouter(prefix="/api/v1/rooms", tags=["Rooms"])


def public_test_cases(test_cases: object) -> list[dict]:
    if not isinstance(test_cases, list):
        return []
    visible = []
    for case in test_cases:
        if not isinstance(case, dict) or case.get("is_hidden"):
            continue
        visible.append({
            "input": case.get("input", ""),
            "expected_output": case.get("expected_output", ""),
        })
    return visible


def question_payload(question: Question) -> dict:
    return {
        "id": str(question.id),
        "title": question.title,
        "description": question.description,
        "difficulty": question.difficulty,
        "time_limit": question.time_limit,
        "memory_limit": question.memory_limit,
        "starter_code": question.starter_code,
        "public_testcases": public_test_cases(question.test_cases),
    }


async def load_players(db: AsyncSession, room_id: UUID) -> list[dict]:
    rows = (
        await db.execute(
            select(RoomPlayer, User)
            .join(User, User.id == RoomPlayer.user_id)
            .where(RoomPlayer.room_id == room_id)
            .order_by(RoomPlayer.joined_at.asc())
        )
    ).all()
    return [
        {
            "user_id": str(user.id),
            "username": user.username,
            "avatar_url": user.avatar_url,
            "rating": user.rating,
            "is_ready": player.is_ready,
            "score": player.score,
        }
        for player, user in rows
    ]


async def room_view(db: AsyncSession, room: Room) -> dict:
    question = None
    if room.status == "PLAYING" and room.question_id is not None:
        loaded = await db.get(Question, room.question_id)
        if loaded is not None:
            question = question_payload(loaded)
    return {
        "room_id": str(room.id),
        "room_code": room.code,
        "host_id": str(room.host_id),
        "game_mode": room.game_mode,
        "status": room.status,
        "problem_set_id": str(room.problem_set_id) if room.problem_set_id else None,
        "question_id": str(room.question_id) if room.question_id else None,
        "started_at": room.started_at.isoformat() if room.started_at else None,
        "players": await load_players(db, room.id),
        "question": question,
    }


async def pick_question(db: AsyncSession, problem_set_id: UUID | None) -> Question | None:
    stmt = (
        select(Question)
        .join(ProblemSet, ProblemSet.id == Question.problem_set_id)
        .where(ProblemSet.is_hidden.is_(False))
    )
    if problem_set_id is not None:
        stmt = stmt.where(Question.problem_set_id == problem_set_id)
    stmt = stmt.order_by(func.random()).limit(1)
    return (await db.execute(stmt)).scalars().first()


async def start_countdown(room_code: str, room_id: UUID) -> None:
    for value in range(3, 0, -1):
        if not manager.is_counting(room_code):
            await manager.broadcast(room_code, {
                "event": "COUNTDOWN_ABORTED",
                "data": {"message": "Người chơi đã rời phòng"},
            })
            return
        await manager.broadcast(room_code, {"event": "COUNTDOWN", "data": {"value": value}})
        await asyncio.sleep(1)

    if not manager.is_counting(room_code):
        await manager.broadcast(room_code, {
            "event": "COUNTDOWN_ABORTED",
            "data": {"message": "Người chơi đã rời phòng"},
        })
        return

    async with AsyncSessionLocal() as db:
        room = await db.get(Room, room_id)
        if room is None or room.status != "WAITING":
            await manager.cancel_countdown(room_code)
            return

        question = await pick_question(db, room.problem_set_id)
        if question is None:
            players = (
                await db.execute(select(RoomPlayer).where(RoomPlayer.room_id == room.id))
            ).scalars().all()
            for player in players:
                player.is_ready = False
            await db.commit()
            await manager.cancel_countdown(room_code)
            await manager.broadcast(room_code, {
                "event": "ERROR",
                "data": {"message": "Không có bài toán khả dụng trong bộ đề"},
            })
            return

        room.question_id = question.id
        room.status = "PLAYING"
        room.started_at = datetime.now(timezone.utc)
        await db.commit()

        if not await manager.confirm_match_start(room_code):
            room.status = "WAITING"
            room.question_id = None
            room.started_at = None
            await db.commit()
            await manager.broadcast(room_code, {
                "event": "COUNTDOWN_ABORTED",
                "data": {"message": "Người chơi đã rời phòng"},
            })
            return

        await manager.broadcast(room_code, {
            "event": "COUNTDOWN_START",
            "data": {
                "message": "START",
                "question": question_payload(question),
            },
        })


async def _reject_other_active_room(db: AsyncSession, user_id: UUID, allowed_room_id: UUID | None = None) -> None:
    active = await get_active_room(db, user_id)
    if active is None or active.id == allowed_room_id:
        return
    raise ConflictException(
        "Bạn đang ở trong một phòng đang hoạt động",
        details={"room_id": str(active.id), "room_code": active.code},
    )


@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=BaseResponse[dict])
async def create_room(
    payload: CustomRoomCreateRequest | None = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _reject_other_active_room(db, current_user.id)
    problem_set_id = payload.problem_set_id if payload else None
    if problem_set_id is not None:
        problem_set = await db.get(ProblemSet, problem_set_id)
        if problem_set is None or problem_set.is_hidden:
            raise NotFoundException("Bộ đề không tồn tại hoặc đã bị ẩn")

    room = Room(
        code=await generate_unique_room_code(db),
        host_id=current_user.id,
        problem_set_id=problem_set_id,
        game_mode="CUSTOM_1V1",
        status="WAITING",
    )
    db.add(room)
    await db.flush()
    db.add(RoomPlayer(room_id=room.id, user_id=current_user.id, is_ready=False))
    await db.commit()
    return BaseResponse(
        message="Tạo phòng thành công",
        data={"room_id": str(room.id), "room_code": room.code},
    )


@router.post("/join", response_model=BaseResponse[dict])
async def join_room(
    payload: JoinRoomRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    code = payload.room_code.strip().upper()
    room = (await db.execute(select(Room).where(Room.code == code))).scalars().first()
    if room is None:
        raise NotFoundException("Không tìm thấy phòng")
    if room.status != "WAITING":
        raise BadRequestException("Phòng đã đầy hoặc trận đấu đang diễn ra")

    players = (
        await db.execute(select(RoomPlayer).where(RoomPlayer.room_id == room.id))
    ).scalars().all()
    if any(player.user_id == current_user.id for player in players):
        return BaseResponse(
            message="Bạn đã ở trong phòng này",
            data={"room_id": str(room.id), "room_code": room.code},
        )

    await _reject_other_active_room(db, current_user.id, allowed_room_id=room.id)
    if len(players) >= 2:
        raise BadRequestException("Phòng đã đầy hoặc trận đấu đang diễn ra")

    db.add(RoomPlayer(room_id=room.id, user_id=current_user.id, is_ready=False))
    await db.commit()
    return BaseResponse(
        message="Vào phòng thành công",
        data={"room_id": str(room.id), "room_code": room.code},
    )


@router.get("/{room_code}", response_model=BaseResponse[dict])
async def get_room(
    room_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    code = room_code.strip().upper()
    room = (await db.execute(select(Room).where(Room.code == code))).scalars().first()
    if room is None:
        raise NotFoundException("Không tìm thấy phòng")
    member = await db.scalar(
        select(RoomPlayer.id).where(
            RoomPlayer.room_id == room.id,
            RoomPlayer.user_id == current_user.id,
        )
    )
    if member is None:
        raise NotFoundException("Không tìm thấy phòng")
    return BaseResponse(data=await room_view(db, room))


@router.websocket("/ws/arena/{room_code}")
async def arena_websocket(
    websocket: WebSocket,
    room_code: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db_ws),
):
    code = room_code.strip().upper()
    user = await get_user_from_token(token, db)
    if user is None:
        await websocket.accept()
        await websocket.close(code=4003, reason="Invalid token")
        return

    room = (await db.execute(select(Room).where(Room.code == code))).scalars().first()
    room_player = None
    if room is not None:
        room_player = (
            await db.execute(
                select(RoomPlayer).where(
                    RoomPlayer.room_id == room.id,
                    RoomPlayer.user_id == user.id,
                )
            )
        ).scalars().first()
    if room is None or room_player is None:
        await websocket.accept()
        await websocket.close(code=4003, reason="User not authorized for this room")
        return

    connected = await manager.connect(websocket, code, user.id)
    if not connected:
        return

    await manager.sync_status(code, room.status)
    await manager.broadcast(code, {
        "event": "JOIN_ROOM",
        "data": {
            "user_id": str(user.id),
            "username": user.username,
            "avatar_url": user.avatar_url,
            "rating": user.rating,
            "players": await load_players(db, room.id),
        },
    })
    await manager.send_personal(code, user.id, {
        "event": "ROOM_STATE",
        "data": await room_view(db, room),
    })

    try:
        while True:
            data = await websocket.receive_json()
            if not isinstance(data, dict):
                continue
            await db.refresh(room)
            await db.refresh(room_player)
            action = data.get("action")

            if action == "player_ready":
                if room.status != "WAITING":
                    await manager.send_personal(code, user.id, {
                        "event": "ERROR",
                        "data": {"message": "Trận đấu đã bắt đầu"},
                    })
                    continue
                room_player.is_ready = True
                await db.commit()
                players = await load_players(db, room.id)
                await manager.broadcast(code, {
                    "event": "PLAYER_READY",
                    "data": {"user_id": str(user.id), "is_ready": True, "players": players},
                })
                if len(players) == 2 and all(player["is_ready"] for player in players):
                    if await manager.begin_countdown(code):
                        manager.track_task(asyncio.create_task(start_countdown(code, room.id)))
                continue

            if action == "player_typing":
                await manager.broadcast(code, {
                    "event": "PLAYER_TYPING",
                    "data": {
                        "user_id": str(user.id),
                        "is_typing": bool(data.get("is_typing", True)),
                    },
                })
                continue

            await manager.send_personal(code, user.id, {
                "event": "ERROR",
                "data": {"message": "Hành động không được hỗ trợ"},
            })
    except WebSocketDisconnect:
        pass
    finally:
        removed = await manager.disconnect(code, user.id, websocket)
        if removed:
            await db.refresh(room)
            if room.status == "WAITING":
                room_player.is_ready = False
                await db.commit()
            await manager.broadcast(code, {
                "event": "PLAYER_LEFT",
                "data": {"user_id": str(user.id), "username": user.username},
            })
