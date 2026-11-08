from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token, parse_user_id
from app.db.database import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def _load_user(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Xác thực Bearer token cho REST API và trả về user đang đăng nhập."""
    credentials_exception = UnauthorizedException(
        message="Could not validate credentials",
        details="Token không hợp lệ hoặc đã hết hạn",
    )
    try:
        payload = decode_access_token(token)
        user_id = parse_user_id(payload)
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await _load_user(db, user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_user_from_token(token: str, db: AsyncSession) -> User | None:
    """Xác thực token cho WebSocket. Trả về None thay vì ném HTTP exception."""
    try:
        payload = decode_access_token(token)
        user_id = parse_user_id(payload)
        if user_id is None:
            return None
        return await _load_user(db, user_id)
    except JWTError:
        return None
