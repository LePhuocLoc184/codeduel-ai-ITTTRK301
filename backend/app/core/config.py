from pydantic import PostgresDsn
from pydantic_settings import SettingsConfigDict, BaseSettings


class Settings(BaseSettings):
    # Định nghĩa các trường cần lấy, và kiểu dữ liệu tương ứng
    PROJECT_NAME: str = "Code Duel 1.0"  # default Value
    DATABASE_URL: PostgresDsn

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()