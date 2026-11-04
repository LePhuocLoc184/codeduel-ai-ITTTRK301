from fastapi import FastAPI, HTTPException, status
from contextlib import asynccontextmanager
from app.db.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- CHẠY KHI BẮT ĐẦU SERVER (STARTUP) ---
    print("🚀 Đang khởi tạo toàn bộ bảng vào PostgreSQL...")
    async with engine.begin() as conn:
        # tạo bảng bất đồng bộ
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Đã khởi tạo các bảng thành công!")

    yield

    # --- CHẠY KHI TẮT SERVER (SHUTDOWN) ---
    print("🛑 Đang đóng kết nối Database...")
    await engine.dispose()

app = FastAPI(
    title="CodeDuel AI API",
    description="CodeDuel API Service",
    lifespan=lifespan
)


@app.get("/health", status_code=status.HTTP_200_OK)
def check_health():
    return "Chào mừng bạn đến với Code Duel"
