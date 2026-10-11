# exam-project

Hệ thống quản lý thi trắc nghiệm trực tuyến – Nhóm 25, môn *Các công nghệ lập trình hiện đại* (core: **FastAPI**).

| Thành phần | Công nghệ |
| --- | --- |
| Backend | FastAPI, SQLAlchemy 2.0 async, Pydantic v2, PyJWT |
| CSDL | PostgreSQL 16 chạy trong Docker (backend và frontend chạy trực tiếp trên máy) |
| Frontend | React 18 + Vite |

Chạy kiểu này: **Docker chỉ chạy PostgreSQL**, còn backend (uvicorn) và frontend (Vite) chạy thẳng trên máy để dễ sửa code và debug.

## 1. Yêu cầu cài đặt

| Công cụ | Phiên bản | Kiểm tra |
| --- | --- | --- |
| Python | 3.12 trở lên | `python --version` |
| Node.js | 18 trở lên | `node --version` |
| Docker Desktop | bản mới, đang chạy | `docker --version` |

## 2. Chạy PostgreSQL bằng Docker

Từ thư mục gốc của repo:

```powershell
docker compose up -d db
docker compose ps          # cột STATUS của db phải là "healthy"
```

Chỉ khởi động service `db` (PostgreSQL 16, cổng `5432`, user/mật khẩu/CSDL đều là `exam`). Dữ liệu nằm trong volume `pgdata` nên không mất khi tắt container.

## 3. Chạy backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # không bắt buộc, mặc định đã khớp Docker; macOS/Linux: cp .env.example .env
python -m app.seed 50                 # nạp 1 admin, 1 giáo viên, 50 sinh viên, 10 câu hỏi, 1 đề (chỉ cần chạy 1 lần)
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- Kiểm tra nhanh: http://localhost:8000/health → `{"status":"ok"}`
- Backend kết nối PostgreSQL trong Docker tại `localhost:5432` (user, mật khẩu, database đều là `exam`). Bảng được tạo tự động khi server khởi động.

Nếu PowerShell báo không cho chạy script `Activate.ps1`, chạy một lần: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## 4. Chạy frontend (React + Vite)

Mở terminal thứ hai:

```powershell
cd frontend
npm install
npm run dev
```

Mở http://localhost:5173. Frontend gọi API tại `http://localhost:8000`; nếu backend chạy cổng khác, tạo `frontend/.env.local` với nội dung `VITE_API_URL=http://localhost:<cổng>`.

## 5. Tài khoản mẫu (chỉ dùng khi phát triển)

| Vai trò | Tên đăng nhập | Mật khẩu |
| --- | --- | --- |
| Admin | `admin01` | `Admin@123` |
| Giáo viên | `teacher01` | `Teacher@123` |
| Sinh viên | `student01` đến `student50` | `Student@123` |

Thử nhanh luồng thi: đăng nhập `student01` → "Làm bài" → chọn đáp án (tự lưu) → "Nộp bài". Đăng nhập `teacher01` → "Bảng điểm" để xem điểm và tải CSV. Giáo viên soạn câu hỏi/tạo đề qua Swagger UI (`/docs`, nút **Authorize**).

## 6. Kiểm thử

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/unit tests/test_architecture.py -v   # nhanh, KHÔNG cần Docker
pytest -v                                         # chạy tất cả, gồm test tích hợp (cần PostgreSQL)
```

| Thư mục | Nội dung | Cần Docker |
| --- | --- | --- |
| `backend/tests/unit/` | Test quy tắc nghiệp vụ và use case bằng repository giả trong bộ nhớ | Không |
| `backend/tests/test_architecture.py` | Kiểm tra ranh giới tầng (domain không import FastAPI/SQLAlchemy...) | Không |
| `backend/tests/integration/` | 18 ca T01–T18 gọi API thật qua `TestClient` | Có: `docker compose up -d db` |

Test tích hợp dùng database riêng `exam_test`, được xoá và tạo lại mỗi lần chạy, nên **không đụng vào dữ liệu thật** trong database `exam`.

## 7. Đo tải

Backend phải đang chạy và đã seed đủ sinh viên. Tắt giới hạn đăng nhập trong `backend/.env` trước khi đo (`RATE_LIMIT_ENABLED=false`) rồi khởi động lại uvicorn.

```powershell
cd backend
python -m bench.load_test io     --base http://localhost:8000 --n 200
python -m bench.load_test exam   --base http://localhost:8000 --users 100 --exam-id 1
python -m bench.load_test resume --base http://localhost:8000 --users 100 --repeat 20 --exam-id 1
python -m bench.load_test ws     --base http://localhost:8000 --users 100 --hold 15 --exam-id 1
```

Muốn đo 200 sinh viên thì seed lại với `docker compose down -v` (xoá CSDL) rồi `python -m app.seed 200`. So sánh bật/tắt cache: đổi `CACHE_ENABLED` trong `backend/.env`, khởi động lại uvicorn rồi chạy lại kịch bản `resume`.

Đếm kết nối PostgreSQL khi đang giữ WebSocket:

```powershell
docker compose exec db psql -U exam -d exam -c "SELECT state, count(*) FROM pg_stat_activity WHERE datname = 'exam' GROUP BY state;"
```

## 8. Biến môi trường (`backend/.env`)

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://exam:exam@localhost:5432/exam` | Chuỗi kết nối PostgreSQL (khớp `docker-compose.yml`) |
| `SECRET_KEY` | giá trị phát triển | Khoá ký JWT, đổi khi triển khai thật |
| `TOKEN_EXPIRE_MINUTES` | `120` | Thời hạn token |
| `CACHE_ENABLED`, `CACHE_TTL_SECONDS` | `true`, `60` | Bật/tắt và thời hạn cache đề |
| `RATE_LIMIT_ENABLED` | `true` | Giới hạn 10 lần đăng nhập mỗi phút mỗi IP |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `20`, `20` | Kích thước pool PostgreSQL |
| `EXPIRY_SCAN_SECONDS` | `5` | Chu kỳ quét bài quá hạn |

## 9. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| `connection refused` tới `localhost:5432` | Docker chưa chạy hoặc `db` chưa `healthy`: `docker compose up -d db` rồi `docker compose ps` |
| Cổng 5432 đang bị PostgreSQL khác chiếm | Tắt PostgreSQL cài trên máy, hoặc đổi cổng trong `docker-compose.yml` (`"5433:5432"`) và trong `DATABASE_URL` |
| `ModuleNotFoundError` khi chạy `python -m app.seed` | Chưa kích hoạt venv hoặc đang đứng sai thư mục: phải ở trong `backend/` |
| Seed in "CSDL đã có dữ liệu, bỏ qua" | Bình thường, dữ liệu đã nạp rồi. Muốn nạp lại: `docker compose down -v` rồi chạy lại từ bước 2 |
| Giao diện báo lỗi mạng / CORS | Backend chưa chạy ở cổng 8000, hoặc frontend chạy cổng khác 5173 (thêm origin vào `CORS_ORIGINS` trong `.env`) |
| Đăng nhập báo 429 | Quá 10 lần/phút; đợi 1 phút hoặc đặt `RATE_LIMIT_ENABLED=false` |

Dọn dẹp: `docker compose down` (giữ dữ liệu) hoặc `docker compose down -v` (xoá cả dữ liệu).

## 10. Cấu trúc thư mục

```text
exam-project/
├─ docker-compose.yml        # chỉ chạy PostgreSQL
├─ backend/                  # FastAPI theo Clean Architecture
│  ├─ app/
│  │  ├─ domain/             # thực thể, quy tắc nghiệp vụ, port và repository (Python thuần)
│  │  ├─ application/        # use case (đăng nhập, bắt đầu thi, chấm điểm, ...)
│  │  ├─ infrastructure/     # PostgreSQL (SQLAlchemy), scrypt, JWT, cache, cấu hình
│  │  ├─ presentation/api/   # router mỏng, schema Pydantic, dependencies, WebSocket
│  │  ├─ main.py             # create_app()
│  │  └─ seed.py             # python -m app.seed
│  ├─ tests/ (unit, integration, test_architecture.py)
│  └─ bench/                 # kịch bản đo tải
├─ frontend/                 # React + Vite + React Router
│  └─ src/
│     ├─ app/                # App, route, ProtectedRoute, AppLayout
│     ├─ pages/              # trang mỏng, chỉ ghép feature và component dùng chung
│     ├─ features/           # auth, exams, attempts, results (api, hook, component riêng)
│     └─ shared/             # httpClient, hooks, ui (Button, Card, DataTable, ...), styles
└─ docs/                     # Báo cáo Nhóm 25 (Bao-cao-Nhom25-FastAPI.docx)
```

Quy tắc phụ thuộc: backend `presentation → application → domain` và `infrastructure → domain` (domain không import tầng nào); frontend `pages → features → shared`. Backend có test tự động bảo vệ ranh giới này (`tests/test_architecture.py`).

Báo cáo đầy đủ: `docs/Bao-cao-Nhom25-FastAPI.docx`.
