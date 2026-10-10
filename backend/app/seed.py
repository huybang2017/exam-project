"""Nạp dữ liệu mẫu: 1 admin, 1 giáo viên, N sinh viên, 10 câu hỏi và 1 đề đã công bố.

Chạy:  python -m app.seed [số_sinh_viên]      (mặc định 50)
Chạy lại nhiều lần an toàn: nếu đã có dữ liệu thì bỏ qua.
"""
import asyncio
import sys
from datetime import timedelta

from sqlalchemy import func, select

from app.database import SessionLocal, init_db
from app.models import Choice, Exam, ExamQuestion, Question, User, utcnow
from app.security import hash_password

QUESTIONS = [
    ("FastAPI chạy trên chuẩn giao tiếp web nào?", ["WSGI", "ASGI", "CGI", "FastCGI"], 1),
    ("Thư viện nào FastAPI dùng để kiểm tra dữ liệu?", ["Marshmallow", "Pydantic", "Cerberus", "Django Forms"], 1),
    ("Đường dẫn mặc định của Swagger UI là gì?", ["/swagger", "/docs", "/api-docs", "/ui"], 1),
    ("Cách khai báo endpoint bất đồng bộ?", ["async def", "def async", "await def", "thread def"], 0),
    ("Cơ chế nào giúp tái sử dụng logic như phiên CSDL hay người dùng hiện tại?",
     ["Dependency Injection", "Biến toàn cục", "Decorator @cache", "Metaclass"], 0),
    ("Mã HTTP FastAPI trả về khi body không đúng schema?", ["400", "404", "422", "500"], 2),
    ("Server ASGI thường dùng để chạy FastAPI?", ["Gunicorn sync worker", "Uvicorn", "Apache mod_wsgi", "Tomcat"], 1),
    ("Tham số hàm có kiểu là một model Pydantic được hiểu là gì?",
     ["Path parameter", "Query parameter", "Request body", "Header"], 2),
    ("Công cụ nào chạy tác vụ sau khi đã trả response?",
     ["BackgroundTasks", "Middleware", "APIRouter", "Depends"], 0),
    ("Giao thức nào FastAPI hỗ trợ để đẩy dữ liệu hai chiều thời gian thực?",
     ["FTP", "WebSocket", "SMTP", "SNMP"], 1),
]


async def seed(n_students: int = 50) -> None:
    await init_db()
    async with SessionLocal() as db:
        if (await db.execute(select(func.count()).select_from(User))).scalar_one() > 0:
            print("CSDL đã có dữ liệu, bỏ qua.")
            return

        admin = User(username="admin01", full_name="Quản trị viên", role="admin",
                     password_hash=hash_password("Admin@123"))
        teacher = User(username="teacher01", full_name="Giáo viên Mẫu", role="teacher",
                       password_hash=hash_password("Teacher@123"))
        student_hash = hash_password("Student@123")  # băm một lần, dùng chung cho dữ liệu mẫu
        students = [User(username=f"student{i:02d}", full_name=f"Sinh viên {i:02d}", role="student",
                         password_hash=student_hash) for i in range(1, n_students + 1)]
        db.add_all([admin, teacher, *students])
        await db.flush()

        questions = []
        for content, choices, correct in QUESTIONS:
            q = Question(content=content, owner_id=teacher.id,
                         choices=[Choice(text=t, is_correct=(i == correct)) for i, t in enumerate(choices)])
            questions.append(q)
        db.add_all(questions)
        await db.flush()

        now = utcnow()
        exam = Exam(title="Kiểm tra FastAPI cơ bản", description="10 câu trắc nghiệm, 15 phút",
                    duration_minutes=15, start_time=now - timedelta(hours=1), end_time=now + timedelta(days=30),
                    is_published=True, owner_id=teacher.id,
                    items=[ExamQuestion(question_id=q.id, position=i, points=1.0) for i, q in enumerate(questions)])
        db.add(exam)
        await db.commit()
        print(f"Đã nạp: 1 admin, 1 giáo viên, {n_students} sinh viên, {len(questions)} câu hỏi, đề #{exam.id}.")


if __name__ == "__main__":
    asyncio.run(seed(int(sys.argv[1]) if len(sys.argv) > 1 else 50))
