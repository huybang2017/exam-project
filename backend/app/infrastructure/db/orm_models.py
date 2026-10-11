"""Mô hình ORM (chi tiết lưu trữ). Schema giữ nguyên từ trước khi refactor; thực thể nghiệp vụ nằm ở domain/entities.py."""
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


def utcnow() -> datetime:
    """UTC không kèm tzinfo (cột DateTime lưu thời gian ngây thơ, luôn hiểu là UTC)."""
    return datetime.now(UTC).replace(tzinfo=None)


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(10), default="student")  # admin | teacher | student
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QuestionORM(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    choices: Mapped[list["ChoiceORM"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="ChoiceORM.id"
    )


class ChoiceORM(Base):
    __tablename__ = "choices"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question: Mapped[QuestionORM] = relationship(back_populates="choices")


class ExamORM(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    items: Mapped[list["ExamQuestionORM"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestionORM.position"
    )


class ExamQuestionORM(Base):
    __tablename__ = "exam_questions"

    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[float] = mapped_column(Float, default=1.0)

    exam: Mapped[ExamORM] = relationship(back_populates="items")
    question: Mapped[QuestionORM] = relationship()


class AttemptORM(Base):
    __tablename__ = "attempts"
    __table_args__ = (
        UniqueConstraint("exam_id", "user_id", name="uq_attempt_exam_user"),
        Index("ix_attempt_open_deadline", "submitted_at", "deadline"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # thang 10
    auto_submitted: Mapped[bool] = mapped_column(Boolean, default=False)


class AttemptAnswerORM(Base):
    __tablename__ = "attempt_answers"

    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    choice_id: Mapped[int] = mapped_column(ForeignKey("choices.id"))
