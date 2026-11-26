# CodeDuel AI

Nền tảng thi đấu lập trình đối kháng 1v1 theo thời gian thực, kết hợp chấm bài tự động, xếp hạng ELO và AI hỗ trợ tạo, rà soát đề bài.

**Đồ án của sinh viên Học viện Công nghệ Bưu chính Viễn thông (PTIT)**
Kho mã nguồn: [LePhuocLoc184/codeduel-ai-ITTTRK301](https://github.com/LePhuocLoc184/codeduel-ai-ITTTRK301)

> **Phạm vi AI hiện tại:** Backend có luồng AI tạo đề và một lượt AI độc lập rà soát đề/test case. Chức năng AI phân tích mã nguồn người chơi sau trận (AI Code Review) chưa được triển khai trong mã nguồn hiện tại.

## Tính năng

- **Tài khoản và hồ sơ:** Đăng ký, đăng nhập bằng JWT; thông tin hồ sơ, avatar, rating, hạng và thống kê trận.
- **Ghép trận 1v1:** Hàng đợi `RANKED_1V1` tự động ghép người chơi theo rating; tạo và tham gia phòng riêng `CUSTOM_1V1` bằng mã phòng.
- **Đấu trường realtime:** Phòng đấu dùng WebSocket để đồng bộ trạng thái sẵn sàng, đếm ngược, tín hiệu đối thủ đang gõ và kết quả trận. Có thể đầu hàng, chạy thử hoặc nộp bài.
- **Chấm bài tự động:** Chạy testcase công khai khi Run; Submit chấm bộ testcase của đề, gồm cả testcase ẩn. Hỗ trợ Python, C++ và Java; có kiểm tra thời gian/bộ nhớ ở tiến trình chấm.
- **Kết quả và xếp hạng:** Trận Ranked cập nhật ELO; trang chủ có leaderboard; hồ sơ hiển thị các trận gần đây và bộ lọc theo chế độ.
- **AI tạo đề:** Khi hai người sẵn sàng, backend có thể nhờ AI tạo đề và rà soát đề/testcase; nếu không khả dụng, hệ thống chọn đề dự phòng từ cơ sở dữ liệu.

## Công nghệ

| Phân hệ | Công nghệ trong dự án |
|---|---|
| Frontend | React/React DOM `^19.0.0`, Vite `^7.1.12`, React Router DOM `^7.9.5`, Axios `^1.13.2`, Tailwind CSS `^3.4.19`, Monaco Editor (`@monaco-editor/react` `^4.7.0`), Lucide React `^0.468.0`, React Markdown `^10.1.0`, remark-gfm `^4.0.1` |
| Backend | Python, FastAPI `0.162.0`, Pydantic `2.14.2`, pydantic-settings `2.16.2`, Uvicorn `0.54.0` |
| Cơ sở dữ liệu | PostgreSQL, SQLAlchemy `2.1.6` (async), asyncpg `0.32.0`, Alembic `1.20.1` |
| Realtime | WebSocket của FastAPI/Starlette; quản lý kết nối/phòng trong bộ nhớ của tiến trình backend |
| Xác thực | JWT qua `python-jose` `3.5.0`; bcrypt qua `passlib` `1.7.4` và `bcrypt` `3.2.2` |
| AI và chấm bài | `httpx` `0.28.1` gọi API OpenAI-compatible hoặc Anthropic; Judge tự quản lý compiler/tiến trình và dùng `psutil` `7.2.2` để theo dõi tài nguyên |

Phiên bản Python và package Python được ghim trong [`backend/requirements.txt`](backend/requirements.txt); phiên bản/range JavaScript nằm trong [`frontend/package.json`](frontend/package.json). Dự án hiện không khai báo Redis hoặc một dịch vụ cache riêng.

## Cấu trúc dự án

```text
.
├── backend/
│   ├── alembic/                  # Cấu hình và các migration
│   ├── app/
│   │   ├── core/                 # Cấu hình, JWT, exception, WebSocket managers
│   │   ├── db/                   # SQLAlchemy, session, seed
│   │   ├── dependencies/         # Dependencies xác thực
│   │   ├── models/               # ORM: user, room, question, submission...
│   │   ├── routers/              # REST API và WebSocket endpoints
│   │   ├── schemas/              # Pydantic request/response
│   │   ├── services/             # Judge, runner, ELO, matchmaking, AI, timer
│   │   └── utils/                # Validator, starter code, helpers
│   ├── code_backup/              # Thư mục runtime lưu code và file build
│   ├── .env.example
│   ├── alembic.ini
│   ├── main.py
│   └── requirements.txt
└── frontend/
    ├── public/
    │   └── src/                  # Source React hiện tại (được import từ index.html)
    │       ├── api/
    │       ├── components/
    │       ├── context/
    │       ├── hooks/
    │       ├── layouts/
    │       ├── pages/
    │       └── routes/
    ├── index.html
    ├── package.json
    └── vite.config.js
```

`code_backup/`, `.venv/`, `node_modules/` và `dist/` là dữ liệu runtime/môi trường cục bộ; không cần tạo thủ công để cài đặt. Source giao diện nằm tại `frontend/public/src` (không phải `frontend/src`).

## Cài đặt và chạy

### Yêu cầu

- Python 3.10 trở lên.
- Node.js và npm tương thích với Vite 7.
- PostgreSQL đang chạy, cùng trình biên dịch/runtime cần thiết nếu muốn chấm từng ngôn ngữ: Python, `g++`, `javac` và `java`.
- Khóa API AI chỉ cần nếu muốn dùng luồng tạo đề AI; khi AI không khả dụng, phòng có thể dùng đề dự phòng.

### 1. Cấu hình backend

Tạo database PostgreSQL, sau đó trong thư mục `backend` tạo `.env` từ file mẫu:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Mở `backend/.env`, thiết lập ít nhất:

```dotenv
DATABASE_URL=postgresql+asyncpg://<user>:<password>@127.0.0.1:5432/<database>
SECRET_KEY=<chuỗi-ngẫu-nhiên-tối-thiểu-32-ký-tự>
```

Để bật AI tạo/rà soát đề, cấu hình thêm `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL` và `AI_BASE_URL` theo nhà cung cấp. Các biến AI được đọc ở backend; không cần tạo `.env.local` cho frontend. Nếu chạy frontend khác origin mặc định, cập nhật `CORS_ORIGINS`.

Khởi tạo schema bằng migration và chạy API:

```powershell
alembic upgrade head
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Thực hiện lệnh trong terminal đã đứng tại `backend` và đã kích hoạt môi trường ảo. Backend cũng khởi tạo metadata bảng và worker ghép trận khi startup.

### 2. Cấu hình frontend

Trong terminal khác, từ thư mục gốc:

```powershell
cd frontend
npm install
npm run dev
```

Mở địa chỉ Vite hiển thị trên terminal (mặc định `http://localhost:5173`). Mặc định Vite proxy `/api` và WebSocket tới `http://localhost:8000`; nếu cần đổi backend, đặt `VITE_API_BASE_URL` trong môi trường frontend.

### 3. Sử dụng nhanh

1. Tạo tài khoản hoặc đăng nhập.
2. Tại đấu trường, tìm trận Ranked hoặc tạo phòng tùy chỉnh rồi chia sẻ mã phòng.
3. Hai người vào phòng và cùng chọn sẵn sàng; sau khi có đề và đếm ngược, viết lời giải trong Monaco Editor.
4. Chạy thử với testcase công khai, sau đó nộp bài để chấm. Trận kết thúc khi một người đạt toàn bộ testcase, đầu hàng hoặc hết giờ.

API docs: `http://localhost:8000/docs`; health check: `http://localhost:8000/health`.

## Một số API và kênh realtime

Các REST endpoint chính (API có xác thực yêu cầu Bearer JWT):

| Phương thức | Endpoint | Mục đích |
|---|---|---|
| `POST` | `/api/v1/auth/register`, `/api/v1/auth/login` | Đăng ký, đăng nhập |
| `GET`, `PUT` | `/api/v1/users/me` | Đọc hồ sơ, cập nhật avatar/mật khẩu |
| `GET` | `/api/v1/users/leaderboard` | Bảng xếp hạng |
| `GET` | `/api/v1/users/{user_id}/history` | Lịch sử các trận gần đây |
| `POST`, `GET` | `/api/v1/rooms/create`, `/api/v1/rooms/{room_code}` | Tạo phòng và đọc trạng thái phòng |
| `POST` | `/api/v1/rooms/join`, `/api/v1/rooms/{room_code}/surrender` | Vào phòng, đầu hàng |
| `POST`, `DELETE`, `GET` | `/api/v1/matchmaking/join`, `/cancel`, `/status` | Vào/hủy hàng đợi, kiểm tra trạng thái |
| `POST` | `/api/v1/execute/run`, `/api/v1/execute/submit` | Chạy thử, nộp bài |
| `POST` | `/api/v1/runner/save-code` | Lưu file code được xác thực |

WebSocket phòng đấu: `/api/v1/rooms/ws/arena/{room_code}?token=<JWT>`. Backend cũng cung cấp `/api/v1/matchmaking/ws?token=<JWT>`; giao diện tìm trận hiện kiểm tra `/api/v1/matchmaking/status` định kỳ. Xem cẩm nang bảo vệ để biết các event và giới hạn triển khai.

## Nhóm phát triển — PTIT

Danh sách dưới đây giữ theo Footer hiện tại trong ứng dụng; hai MSSV đang là nội dung chờ nhóm bổ sung:

| Thành viên | MSSV | Phân công hiển thị |
|---|---|---|
| Lê Phước Lộc | N25DTCN100 | Backend & FrontEnd support |
| Nguyễn Đức Huy 2 | B25DTCN026 | Backend & Judge Engine |
| Hoàng Dương Nam | `[Điền MSSV]` | Backend & Judge Engine |
| Nguyễn Đức Huy 4 | `[Điền MSSV]` | UI/UX & Testing |

## Tài liệu

- [Cẩm nang ôn tập và bảo vệ đồ án](docs/TAI_LIEU_BAO_VE_DU_AN.md)
- [Danh sách dependency Backend](backend/requirements.txt)
- [Dependencies và scripts Frontend](frontend/package.json)
