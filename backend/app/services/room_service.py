import random
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InternalServerErrorException
from app.models import Room, RoomPlayer

ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


async def generate_unique_room_code(db: AsyncSession, length: int = 6) -> str:
    """Sinh mã PIN 6 ký tự, kiểm tra trùng trên toàn bộ bảng rooms."""
    for _ in range(10):
        code = "".join(random.choices(ROOM_CODE_ALPHABET, k=length))
        existing = await db.scalar(select(Room.id).where(Room.code == code))
        if existing is None:
            return code
    raise InternalServerErrorException("Không thể sinh mã phòng duy nhất")


async def get_active_room(db: AsyncSession, user_id: UUID) -> Room | None:
    """Phòng WAITING hoặc PLAYING mà user đang tham gia."""
    stmt = (
        select(Room)
        .join(RoomPlayer, RoomPlayer.room_id == Room.id)
        .where(
            RoomPlayer.user_id == user_id,
            Room.status.in_(("WAITING", "PLAYING")),
        )
        .order_by(Room.created_at.desc())
    )
    return (await db.execute(stmt)).scalars().first()
