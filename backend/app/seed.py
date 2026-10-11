"""Nạp dữ liệu mẫu: 1 admin, 1 giáo viên, N sinh viên, 10 câu hỏi và 1 đề đã công bố.

Chạy:  python -m app.seed [số_sinh_viên]      (mặc định 50)
Chạy lại nhiều lần an toàn: nếu đã có dữ liệu thì bỏ qua.
"""
import asyncio
import sys
from datetime import timedelta

from app.domain.entities import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, Choice, Exam, ExamItem, Question, User
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.engine import SessionLocal, init_db
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.security.scrypt_hasher import ScryptHasher

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
    hasher = ScryptHasher()
    async with SqlAlchemyUnitOfWork(SessionLocal) as uow:
        if await uow.users.count() > 0:
            print("CSDL đã có dữ liệu, bỏ qua.")
            return

        await uow.users.add(User("admin01", "Quản trị viên", ROLE_ADMIN, await hasher.hash("Admin@123")))
        teacher = await uow.users.add(User("teacher01", "Giáo viên Mẫu", ROLE_TEACHER, await hasher.hash("Teacher@123")))
        student_hash = await hasher.hash("Student@123")  # băm một lần, dùng chung cho dữ liệu mẫu
        for i in range(1, n_students + 1):
            await uow.users.add(User(f"student{i:02d}", f"Sinh viên {i:02d}", ROLE_STUDENT, student_hash))

        questions = [
            await uow.questions.add(
                Question(content, teacher.id, [Choice(t, is_correct=(i == correct)) for i, t in enumerate(choices)])
            )
            for content, choices, correct in QUESTIONS
        ]

        now = SystemClock().now()
        exam = await uow.exams.add(
            Exam(title="Kiểm tra FastAPI cơ bản", description="10 câu trắc nghiệm, 15 phút", duration_minutes=15,
                 start_time=now - timedelta(hours=1), end_time=now + timedelta(days=30), owner_id=teacher.id,
                 is_published=True, items=[ExamItem(q.id, 1.0, i) for i, q in enumerate(questions)])
        )
        await uow.commit()
        print(f"Đã nạp: 1 admin, 1 giáo viên, {n_students} sinh viên, {len(questions)} câu hỏi, đề #{exam.id}.")


if __name__ == "__main__":
    asyncio.run(seed(int(sys.argv[1]) if len(sys.argv) > 1 else 50))
