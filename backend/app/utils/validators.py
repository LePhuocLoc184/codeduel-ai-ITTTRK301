from pydantic import TypeAdapter, EmailStr, ValidationError
from app.core.exceptions import BadRequestException

_email_adapter = TypeAdapter(EmailStr)


def _normalize_email(value: str) -> str:
    try:
        return str(_email_adapter.validate_python(value.strip().lower()))
    except ValidationError:
        raise BadRequestException("Email không hợp lệ")


def _normalize_username(value: str) -> str:
    username = value.strip()
    if not 3 <= len(username) <= 50:
        raise BadRequestException("Username phải từ 3 đến 50 ký tự")
    if not all(char.isalnum() or char == "_" for char in username):
        raise BadRequestException("Username chỉ gồm chữ, số và dấu gạch dưới")
    return username.lower()  # đồng bộ userName viết thường để search nhanh



def _truncate_password(password: str) -> str:
    """Cắt mật khẩu về tối đa 72 bytes UTF-8 để tương thích an toàn tuyệt đối với

    bcrypt backend bên dưới passlib.
    """
    return password.encode("utf-8")[:72].decode("utf-8", errors="ignore")