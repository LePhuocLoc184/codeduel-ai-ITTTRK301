
from pydantic import PostgresDsn, Field
from pydantic_settings import SettingsConfigDict, BaseSettings


class Settings(BaseSettings):
    # Định nghĩa các trường cần lấy, và kiểu dữ liệu tương ứng
    PROJECT_NAME: str = "Code Duel 1.0"  # default Value
    DATABASE_URL: PostgresDsn

    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = (60 * 24) * 7

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    CORS_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(:\d+)?$"

    # trả về Array list các cors đã thiết lập

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
