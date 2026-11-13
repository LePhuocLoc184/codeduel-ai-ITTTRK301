from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import engine
from app.models import Base

# Schemas
from app.schemas.response import BaseResponse

# CORE
from app.core.handlers import register_exception_handlers
from app.core.exceptions import NotFoundException, BadRequestException
from app.core.config import settings
from app.routers.arena import router as arena_router
from app.routers.auth import router as auth_router
from app.routers.matchmaking import router as matchmaking_router
from app.routers.users import router as user_router


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

# đăng kí global exception
register_exception_handlers(app)

# đăng kí các router vào app
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(arena_router)
app.include_router(matchmaking_router)

# thiết lập vùng trung gian giới hạn các Miền có thể gửi được Request đến BackEnd
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
def check_health():
    return {"message": "Chào mừng bạn đến với Code Duel"}


# tạm thời để test các exception và baseResponse trả về nha ae

# thành công
@app.get("/test/success", status_code=status.HTTP_200_OK)
async def test_success_case():
    return BaseResponse(
        message="Thành công rồi nha ông",
        data={
            "username": "Lê Phước Lộc",
        }
    )


# thất bại lỗi 4.. do client
@app.get("/test/not-found", status_code=status.HTTP_404_NOT_FOUND)
async def test_not_found():
    raise NotFoundException(
        message="không tìm thấy bài tập này"
    )


# thất bại do truyền sai request body
@app.post("/test/validation-test/{user_id}", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
async def test_validation_request(user_id: int):

    return BaseResponse(data={"user_id": user_id})


# thất bại lỗi từ servergit
@app.post("/test/server-error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
async def test_server_error():
    return 1 / 0
