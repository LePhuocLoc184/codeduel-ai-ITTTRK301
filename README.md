# CodeDuel AI — Nền Tảng Thi Đấu Lập Trình Đối Kháng Thời Gian Thực

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.162.0-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19.0.0-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/Vite-7.1.12-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/PostgreSQL-14%2B-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="License: MIT" />
</p>

---

## 1. Tên dự án & Mô tả ngắn

**CodeDuel AI** là nền tảng thi đấu lập trình đối kháng 1v1 trực tiếp thời gian thực, kết hợp công nghệ AI hỗ trợ ra đề, kiểm duyệt thuật toán và phân tích tối ưu mã nguồn sau trận đấu. Dự án giải quyết sự đơn điệu và thiếu tính tương tác trong việc rèn luyện thuật toán truyền thống, biến việc luyện code thành những trận đấu trí tốc độ cao với thanh tiến độ thời gian thực (Health/Progress bar) và hệ thống xếp hạng Elo minh bạch.

---

## 2. Tính năng chính

- 🔐 **Xác thực người dùng an toàn:** Đăng ký, đăng nhập tài khoản với JWT (JSON Web Tokens), mã hóa mật khẩu bcrypt, quản lý phiên độc lập đa tab qua `sessionStorage` & `localStorage`.
- ⚔️ **Đấu trường 1v1 thời gian thực (Arena & Matchmaking):**
  - **Ghép trận tự động (Matchmaking Queue):** Cơ chế hàng đợi thông minh với Worker nền ghép nối hai đấu thủ phù hợp theo thứ tự hàng đợi hoặc hệ số Elo.
  - **Tạo phòng đấu tùy chỉnh (Custom Room):** Tạo phòng riêng biệt, chia sẻ mã mời phòng (Room Code 6 ký tự) để thách đấu trực tiếp với bạn bè.
  - **Đồng bộ song song qua WebSocket:** Cập nhật thời gian thực trạng thái gõ phím (typing throttle 1s), tiến độ vượt testcase (thanh máu), trạng thái sẵn sàng và đếm ngược bắt đầu trận.
- 💻 **Trình soạn thảo & Chấm code đa ngôn ngữ (Sandbox & Runner):**
  - Tích hợp Monaco Editor hỗ trợ cú pháp đa ngôn ngữ: **Python 3**, **C++ (g++)**, **Java (javac/java)**.
  - Bộ chấm giải thuật (Judge & Execution Worker): Đo đạc thời gian thực thi (ms), bộ nhớ RAM RSS tiêu thụ (`psutil`), tự động ngắt khi chạm ngưỡng `time_limit` (TLE) hoặc `memory_limit` (MLE).
  - Tách bạch giữa **Run Code** (chạy thử với testcase công khai) và **Submit Code** (chấm điểm toàn diện với testcase ẩn).
- 🤖 **Trợ lý AI Đấu trường (AI Assistant & Review):**
  - Tự động sinh đề bài thi đấu theo chủ đề và độ khó yêu cầu với cấu trúc chuẩn.
  - Kiểm duyệt đề độc lập, xác minh tính đúng đắn của testcase biên và lời giải tham chiếu.
  - Đánh giá mã nguồn sau trận đấu (AI Review Report): So sánh độ phức tạp Big-O ($O(N)$, $O(1)$...), đánh giá quy chuẩn Clean Code và đề xuất mã nguồn tối ưu hoàn chỉnh.
- 🏆 **Hệ thống Xếp hạng (Leaderboard) & Hồ sơ cá nhân:**
  - Thuật toán tính điểm Elo biến thiên linh hoạt theo kết quả thắng/thua và đối thủ.
  - Bảng vinh danh Top Coder toàn cầu với huy hiệu bậc hạng (Rank Badge: Bronze, Silver, Gold...), thống kê tỉ lệ thắng (Win Rate).

### Ảnh minh họa giao diện (Screenshots & Demos)

| Đấu trường trực tiếp 1v1 | Phân tích mã nguồn AI Review |
| :---: | :---: |
| ![Arena Preview](docs/images/arena.png)<br>*(Giao diện soạn thảo mã nguồn & đồng bộ tiến độ thời gian thực)* | ![AI Review Preview](docs/images/ai-review.png)<br>*(Báo cáo Big-O & Clean Code do AI phân tích sau trận)* |

| Bảng xếp hạng Elo | Sảnh chờ ghép trận |
| :---: | :---: |
| ![Leaderboard Preview](docs/images/leaderboard.png)<br>*(Bảng vinh danh Top Coders & thống kê tỷ lệ thắng)* | ![Matchmaking Preview](docs/images/matchmaking.png)<br>*(Tìm kiếm trận đấu tự động & sảnh chờ phòng thi đấu)* |

---

## 3. Yêu cầu tiên quyết (Prerequisites)

Trước khi tiến hành cài đặt, hãy đảm bảo máy tính của bạn đã cài đặt các công cụ sau:

- **Python:** Phiên bản `3.10` trở lên (Khuyến nghị Python 3.11 hoặc 3.12).
- **Node.js:** Phiên bản `18.x` hoặc `20.x` trở lên kèm trình quản lý gói `npm`.
- **PostgreSQL Database:** Phiên bản `14.x` trở lên (đang hoạt động trên cổng mặc định `5432`).
- **Trình biên dịch mã nguồn (để hỗ trợ bộ chấm Runner/Judge cục bộ):**
  - **Python 3:** Lệnh `python` hoặc `python3` trong PATH.
  - **GCC / G++:** Lệnh `g++` hỗ trợ chuẩn C++17 trở lên.
  - **JDK:** Lệnh `javac` và `java` (phiên bản OpenJDK 17 hoặc 21).
- **Git:** Quản lý mã nguồn phiên bản.

---

## 4. Cấu trúc thư mục (Project Structure)

```text
codeduel-ai-ITTTRK301/
├── backend/                        # Nguồn dịch vụ Backend (FastAPI, Python)
│   ├── alembic/                    # Quản lý Database Migrations (Alembic)
│   │   ├── versions/               # Lịch sử các file migration theo phiên
│   │   └── env.py                  # Cấu hình môi trường kết nối Alembic
│   ├── app/
│   │   ├── core/                   # Cấu hình hệ thống, Security JWT, WebSocket Manager
│   │   │   ├── config.py           # Đọc và xác thực biến môi trường (Pydantic BaseSettings)
│   │   │   ├── security.py         # Hash mật khẩu (bcrypt), sinh & giải mã JWT Token
│   │   │   ├── socket_manager.py   # Connection Manager quản lý Socket phòng đấu 1v1
│   │   │   └── matchmaking_socket.py # Socket phục vụ sảnh ghép trận tự động
│   │   ├── db/                     # Khởi tạo kết nối SQLAlchemy Engine & Dữ liệu mẫu
│   │   │   ├── database.py         # AsyncSessionLocal & kết nối asyncpg PostgreSQL
│   │   │   └── seed.py             # Script nạp tài khoản và bộ đề thi đấu mẫu
│   │   ├── models/                 # Khai báo cấu trúc bảng cơ sở dữ liệu (SQLAlchemy ORM)
│   │   │   ├── users.py, rooms.py, questions.py, submissions.py...
│   │   ├── routers/                # Các tầng Controller REST API & WebSocket Endpoints
│   │   │   ├── auth.py             # API Đăng ký, đăng nhập, cấp phát Access Token
│   │   │   ├── users.py            # API Hồ sơ người dùng, thống kê, Bảng xếp hạng Elo
│   │   │   ├── arena.py            # API & WebSocket phòng đấu 1v1
│   │   │   ├── matchmaking.py      # API & WebSocket tìm trận tự động
│   │   │   ├── runner.py           # API nhận và lưu trữ mã nguồn tạm thời
│   │   │   └── execute.py          # API kích hoạt chạy thử & nộp bài thi đấu
│   │   ├── schemas/                # Khai báo DTO / Data Validation (Pydantic models)
│   │   ├── services/               # Xử lý nghiệp vụ (Judge, Elo rating, Worker timers)
│   │   │   ├── judge.py            # Bộ chấm code, so khớp kết quả testcase, đo RAM/CPU
│   │   │   ├── elo.py              # Thuật toán tính toán điểm xếp hạng Elo
│   │   │   ├── matchmaking_worker.py # Background Worker liên tục ghép cặp người chơi
│   │   │   └── match_timer.py      # Xử lý đếm ngược và tự động kết thúc trận khi hết giờ
│   │   └── utils/                  # Các hàm tiện ích hỗ trợ
│   ├── alembic.ini                 # Cấu hình công cụ di chuyển dữ liệu Alembic
│   ├── main.py                     # Entrypoint khởi tạo FastAPI App, CORS, Lifespan
│   └── requirements.txt            # Danh sách gói phụ thuộc Python
│
├── frontend/                       # Nguồn giao diện người dùng (React, Vite, Tailwind CSS)
│   ├── public/                     # Thư mục mã nguồn và tài nguyên tĩnh
│   │   └── src/                    # Kiến trúc ứng dụng Frontend
│   │       ├── api/                # Cấu hình gọi API
│   │       │   ├── axios.js        # Axios instance, Interceptors tự gán Bearer Token
│   │       │   └── aiClient.js     # Tích hợp trực tiếp SDK Gemini, OpenAI, Claude
│   │       ├── components/         # Các thành phần tái sử dụng (Navbar, Avatar, Footer...)
│   │       │   └── arena/          # UI phòng đấu (Monaco Editor, Console, Problem, AI Review)
│   │       ├── context/            # Quản lý State toàn cục (AuthContext)
│   │       ├── layouts/            # Khung giao diện chính (MainLayout)
│   │       ├── pages/              # Các màn hình chính (Dashboard, Arena, Room, Matchmaking...)
│   │       ├── routes/             # Thiết lập định tuyến trang (AppRoutes)
│   │       ├── App.jsx             # Gốc khởi chạy component
│   │       └── main.jsx            # Entrypoint render ReactDOM
│   ├── index.html                  # Khung HTML gốc của Vite
│   ├── package.json                # Cấu hình dependencies & scripts của NPM
│   ├── tailwind.config.js          # Cấu hình hệ thống thiết kế Tailwind CSS
│   └── vite.config.js              # Cấu hình đóng gói Vite & Proxy
│
└── README.md                       # Tài liệu hướng dẫn kỹ thuật dự án
```

---

## 5. Cấu hình / Biến môi trường (Environment Variables)

### 5.1. Backend (`backend/.env`)

Tạo file `backend/.env` từ file mẫu `backend/.env.example` và cấu hình các giá trị:

| Tên biến | Bắt buộc | Mô tả | Giá trị mẫu |
| :--- | :---: | :--- | :--- |
| `PROJECT_NAME` | Không | Tên hiển thị của dự án | `Code Duel 1.0` |
| `DATABASE_URL` | **Có** | Chuỗi kết nối PostgreSQL (AsyncPG) | `postgresql+asyncpg://postgres:password123@127.0.0.1:5432/codeduel_db` |
| `SECRET_KEY` | **Có** | Khóa bí mật dùng để ký và giải mã JWT token (tối thiểu 32 ký tự) | `my_super_secret_jwt_key_at_least_32_characters_long_123` |
| `ALGORITHM` | Không | Thuật toán băm chữ ký JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Không | Thời gian hết hạn của Access Token (phút) | `10080` *(7 ngày)* |
| `CORS_ORIGINS` | Không | Danh sách tên miền Frontend được phép gửi request (phân cách bởi dấu phẩy) | `http://localhost:5173,http://127.0.0.1:5173` |

### 5.2. Frontend (`frontend/.env.local`)

Tạo file `frontend/.env.local` từ file mẫu `frontend/.env.local.example`:

| Tên biến | Bắt buộc | Mô tả | Giá trị mẫu |
| :--- | :---: | :--- | :--- |
| `VITE_API_BASE_URL` | Không | URL gốc gọi đến API Backend (nếu không set sẽ dùng `/` proxy) | `http://localhost:8000` |
| `VITE_AI_PROVIDER` | **Có** | Nhà cung cấp AI (`gemini`, `openai`, `anthropic`, `openrouter`, `custom`) | `gemini` |
| `VITE_AI_API_KEY` | **Có** | Khóa API của mô hình AI bạn chọn (Gemini API Key hoặc OpenAI API Key) | `AIzaSyYourGeminiApiKeyHere12345` |
| `VITE_AI_MODEL` | Không | Tên model AI tương ứng | `gemini-1.5-flash` hoặc `gemini-2.0-flash` |
| `VITE_AI_BASE_URL` | Không | Base URL tùy biến (chỉ bắt buộc khi chọn provider `custom`) | `https://generativelanguage.googleapis.com/v1beta/openai` |

---

## 6. Cài đặt (Installation)

Thực hiện lần lượt các bước sau từ terminal để thiết lập mã nguồn dự án:

### Bước 1: Clone Repository
```bash
git clone https://github.com/LePhuocLoc184/codeduel-ai-ITTTRK301.git
cd codeduel-ai-ITTTRK301
```

### Bước 2: Cài đặt và Cấu hình Backend
Mở một cửa sổ dòng lệnh và di chuyển vào thư mục `backend`:

```bash
cd backend

# 1. Khởi tạo và kích hoạt môi trường ảo Python
# Trên Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Trên Linux/macOS:
# python3 -m venv .venv
# source .venv/bin/activate

# 2. Cài đặt các thư viện phụ thuộc
pip install --upgrade pip
pip install -r requirements.txt

# 3. Tạo file cấu hình môi trường
copy .env.example .env
# (Lưu ý mở file .env và cập nhật lại DATABASE_URL, SECRET_KEY tương ứng với máy của bạn)

# 4. Chạy migration để khởi tạo các bảng cơ sở dữ liệu
alembic upgrade head

# 5. (Tùy chọn) Nạp dữ liệu tài khoản và bài tập mẫu để trải nghiệm ngay
python -m app.db.seed
```

> **Ghi chú dữ liệu Seed:** Khi chạy lệnh `python -m app.db.seed`, hệ thống sẽ nạp sẵn các tài khoản demo (mật khẩu mặc định: `Password123`):
> - `phuoc_loc_dev` (Admin, Rating: 1850)
> - `tran_finance` (User, Rating: 1620)
> - `algo_master` (User, Rating: 1950)

### Bước 3: Cài đặt và Cấu hình Frontend
Mở một cửa sổ dòng lệnh mới và di chuyển vào thư mục `frontend`:

```bash
cd frontend

# 1. Cài đặt các gói npm phụ thuộc
npm install

# 2. Tạo file cấu hình môi trường AI cục bộ
copy .env.local.example .env.local
# (Mở file .env.local và điền VITE_AI_API_KEY của bạn để sử dụng các tính năng AI)
```

---

## 7. Cách sử dụng (Usage)

### 7.1. Khởi chạy dự án

**1. Khởi chạy Backend Server (FastAPI):**
```bash
cd backend
# Đảm bảo đã kích hoạt .venv
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
- Máy chủ Backend sẽ chạy tại: `http://localhost:8000`
- Tài liệu kiểm thử tương tác API (Swagger UI): **`http://localhost:8000/docs`**
- Tài liệu chi tiết ReDoc: **`http://localhost:8000/redoc`**

**2. Khởi chạy Frontend Dev Server (Vite):**
```bash
cd frontend
npm run dev
```
- Ứng dụng Web sẽ hoạt động tại: **`http://localhost:5173`**

### 7.2. Luồng trải nghiệm ứng dụng cơ bản

```text
[Đăng ký / Đăng nhập] ──> [Bảng tin Dashboard] ──> [Chọn chế độ: Ghép ngẫu nhiên / Tạo phòng]
                                                              │
                                                              ▼
[Kết thúc trận] <── [AI Phân tích Big-O & Clean Code] <── [Thi đấu 1v1 trên Arena]
```

1. **Đăng nhập:** Mở trình duyệt tại `http://localhost:5173`, chọn **Đăng nhập** với tài khoản `phuoc_loc_dev` (mật khẩu `Password123`) hoặc tạo tài khoản mới.
2. **Bắt đầu trận đấu:**
   - **Cách 1 (Tạo phòng riêng):** Vào mục **Phòng đấu** $\rightarrow$ Tạo phòng, chia sẻ mã phòng gồm 6 ký tự cho người chơi khác mở trên trình duyệt khác/cửa sổ ẩn danh để cùng tham gia.
   - **Cách 2 (Tìm trận tự động):** Bấm **Tìm trận** $\rightarrow$ Hệ thống tự động đưa bạn vào hàng đợi và ghép cặp đối kháng.
3. **Thi đấu:**
   - Màn hình thi đấu xuất hiện với đề bài thuật toán, ví dụ testcase công khai và bộ gõ Monaco Editor.
   - Khi gõ code, thanh tiến độ và tín hiệu đối thủ sẽ liên tục đồng bộ qua WebSocket.
   - Bấm **Chạy thử** để kiểm tra mã với testcase công khai.
   - Bấm **Nộp bài** để gửi bài chấm chính thức qua toàn bộ testcase ẩn. Người vượt qua 100% testcase nhanh hơn sẽ giành chiến thắng.
4. **Tổng kết & AI Review:** Trận đấu kết thúc, hệ thống tự động cộng/trừ điểm Elo và trợ lý AI sẽ trả về bảng phân tích độ phức tạp thời gian/bộ nhớ và mã nguồn tối ưu tương ứng.

---

## 8. Chạy kiểm thử (Running Tests)

### Kiểm thử Backend API
Kiểm tra tính sẵn sàng của dịch vụ qua Endpoint Health Check:
```bash
# Kiểm tra trạng thái hoạt động của Backend
curl http://localhost:8000/health
```

Chạy kiểm thử tự động với `pytest` (nếu có bổ sung test suite):
```bash
cd backend
pytest -v
```

### Kiểm tra cú pháp Frontend
Kiểm tra quá trình biên dịch và build tối ưu hóa gói ứng dụng Frontend:
```bash
cd frontend
npm run build
```

---

## 9. Đóng góp (Contributing)

Dự án hoan nghênh mọi đóng góp xây dựng và nâng cấp từ các thành viên trong nhóm phát triển. Vui lòng tuân thủ quy trình sau:

### 9.1. Quy tắc đặt tên nhánh (Branch Naming)
- Tính năng mới: `feature/<tên-tính-năng>` hoặc `feature/<ma-task>-<mo-ta-ngan>` (Ví dụ: `feature/ai-review-gemini`, `feature/room-chat`)
- Sửa lỗi: `fix/<tên-lỗi>` (Ví dụ: `fix/compiler-java-path`, `fix/websocket-reconnect`)
- Tối ưu / Tái cấu trúc: `refactor/<tên-nội-dung>` (Ví dụ: `refactor/judge-service`)

### 9.2. Chuẩn viết Commit Message
Áp dụng định dạng **Conventional Commits**:
- `feat:` Thêm tính năng mới cho dự án.
- `fix:` Khắc phục lỗi phát sinh.
- `refactor:` Tái cấu trúc mã nguồn nhưng không đổi logic xử lý.
- `docs:` Cập nhật tài liệu kỹ thuật, hướng dẫn.
- `style:` Chỉnh sửa định dạng giao diện, CSS, khoảng trắng, format code.
- `chore:` Thay đổi cấu hình build, thêm thư viện phụ thuộc.

*Ví dụ:*
```bash
git commit -m "feat: tich hop socket thong bao tien do nop bai arena"
git commit -m "fix: sua loi timeout khi chay testcase ngon ngu c++"
```

### 9.3. Quy trình gửi Pull Request (PR)
1. Fork hoặc clone repo về máy làm việc.
2. Tạo nhánh mới từ `main` theo đúng quy ước.
3. Hoàn thiện code, đảm bảo đã chạy thử cục bộ và không có lỗi biên dịch.
4. Push nhánh lên GitHub và tạo Pull Request (PR) hướng về nhánh `main`.
5. Mô tả chi tiết các thay đổi trong PR, gắn thẻ (tag) reviewer và chờ ít nhất 1 thành viên kiểm tra (Code Review) trước khi merge.

---

## 10. Giấy phép và Liên hệ (License & Contact)

### Giấy phép (License)
Dự án được phân phối dưới giấy phép mã nguồn mở **MIT License**. Bạn có toàn quyền sử dụng, sửa đổi và phân phối theo các điều khoản quy định.

### Đội ngũ phát triển (Development Team)
- **Học viện Công nghệ Bưu chính Viễn thông (PTIT) & Rikkeisoft Education**
- **Đại diện kỹ thuật:** Lê Phước Lộc (`phuoc_loc_dev`)
- **Kho lưu trữ dự án:** [GitHub Repository](https://github.com/LePhuocLoc184/codeduel-ai-ITTTRK301)
- **Hỗ trợ & Báo lỗi:** Mọi thắc mắc hoặc báo lỗi kỹ thuật vui lòng mở [GitHub Issues](https://github.com/LePhuocLoc184/codeduel-ai-ITTTRK301/issues).
