from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Khởi tạo CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _truncate_password(password: str) -> str:
    """Cắt mật khẩu về tối đa 72 bytes UTF-8 để tương thích an toàn tuyệt đối với

    bcrypt backend bên dưới passlib.
    """
    return password.encode("utf-8")[:72].decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng CryptContext (đã xử lý bẫy 72 bytes)."""
    safe_password = _truncate_password(password)
    return pwd_context.hash(safe_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác thực mật khẩu thô với chuỗi hash trong DB."""
    if not hashed_password or not plain_password:
        return False
    try:
        safe_password = _truncate_password(plain_password)
        return pwd_context.verify(safe_password, hashed_password)
    except (ValueError, TypeError, Exception):
        return False


def create_access_token(
    user_id: UUID | str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Tạo JWT Access Token linh hoạt."""
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Giải mã và verify chữ ký/thời hạn của JWT token."""
    return jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )


def parse_user_id(payload: dict[str, Any]) -> UUID | None:
    """Trích xuất và parse user_id từ claim 'sub' trong payload JWT."""
    subject = payload.get("sub")
    if not subject:
        return None
    try:
        return UUID(str(subject))
    except (ValueError, TypeError):
        return None
