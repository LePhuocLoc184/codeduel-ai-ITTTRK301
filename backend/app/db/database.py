from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings


# khởi tạo Async Engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=True,  # In ra các câu lệnh SQL để dễ debug lúc dev
    future=True
)

# 2. Khởi tạo Async Session Maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 3. Dependency cấp Session cho FastAPI Routers


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

