from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.users import (
    TokenResponse,
    UserBaseResponse,
    UserLoginRequest,
    UserRegisterSchema,
    UserRole,
)
from app.utils import validators


def create_token_response(user: User) -> TokenResponse:
    """Tạo đối tượng TokenResponse kèm access token và thông tin user cơ bản."""
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=UserBaseResponse.model_validate(user),
    )


async def find_duplicate_user(
    db: AsyncSession, username: str, email: str
) -> User | None:
    """Kiểm tra xem username hoặc email đã tồn tại trong DB chưa (tận dụng

    Index).
    """
    stmt = select(User).where((User.username == username) | (User.email == email))
    return (await db.execute(stmt)).scalars().first()


async def register_user(
    db: AsyncSession, payload: UserRegisterSchema
) -> TokenResponse:
    """Xử lý chuẩn hóa dữ liệu, kiểm tra trùng lặp và tạo tài khoản mới."""
    username = validators. _normalize_username(payload.username)
    email = validators._normalize_email(payload.email)

    if await find_duplicate_user(db, username, email):
        raise ConflictException("Username hoặc email đã tồn tại")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER.value if hasattr(UserRole, "USER") else "user",
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictException("Username hoặc email đã tồn tại")

    await db.refresh(user)
    return create_token_response(user)


async def authenticate_user(
    db: AsyncSession, payload: UserLoginRequest
) -> TokenResponse:
    """Xác thực thông tin đăng nhập và trả về access token."""
    email = validators._normalize_email(payload.email)

    # Tối ưu: Query trực tiếp trên indexed column User.email (không dùng func.lower)
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalars().first()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedException("Email hoặc mật khẩu không đúng")

    return create_token_response(user)