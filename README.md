# exam-project

Hệ thống quản lý thi trắc nghiệm trực tuyến – Nhóm 25, môn *Các công nghệ lập trình hiện đại* (core: **FastAPI**).

| Thành phần | Công nghệ |
| --- | --- |
| Backend | FastAPI, SQLAlchemy 2.0 async, Pydantic v2, PyJWT |
| CSDL | PostgreSQL 16 (Docker); SQLite khi chạy test |
| Frontend | React 18 + Vite |

## Chạy hệ thống

```bash
cp .env.example .env
docker compose up -d --build                       # PostgreSQL + API (http://localhost:8000/docs)
docker compose exec api python -m app.seed 50      # 1 admin, 1 giáo viên, 50 sinh viên, 10 câu hỏi, 1 đề
cd frontend && npm install && npm run dev          # http://localhost:5173
```

Tài khoản mẫu (chỉ dùng khi phát triển): `admin01 / Admin@123`, `teacher01 / Teacher@123`, `student01..student50 / Student@123`.

## Kiểm thử và đo tải

```bash
cd backend && pip install -r requirements.txt && pytest -v
docker compose exec api python -m bench.load_test exam --base http://localhost:8000 --users 100 --exam-id 1
```

Báo cáo đầy đủ: `docs/Bao-cao-Nhom25-FastAPI.docx`.
