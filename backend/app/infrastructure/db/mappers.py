"""Đổi qua lại giữa mô hình ORM và thực thể nghiệp vụ."""
from app.domain.entities import Attempt, Choice, Exam, ExamItem, Question, User
from app.infrastructure.db.orm_models import AttemptORM, ChoiceORM, ExamORM, QuestionORM, UserORM


def to_user(o: UserORM) -> User:
    return User(o.username, o.full_name, o.role, o.password_hash, o.id)


def to_question(o: QuestionORM) -> Question:
    return Question(o.content, o.owner_id, [Choice(c.text, c.is_correct, c.id) for c in o.choices], o.id)


def question_to_orm(q: Question) -> QuestionORM:
    return QuestionORM(content=q.content, owner_id=q.owner_id,
                       choices=[ChoiceORM(text=c.text, is_correct=c.is_correct) for c in q.choices])


def to_exam(o: ExamORM) -> Exam:
    return Exam(
        title=o.title, description=o.description, duration_minutes=o.duration_minutes,
        start_time=o.start_time, end_time=o.end_time, owner_id=o.owner_id, is_published=o.is_published,
        items=[ExamItem(i.question_id, i.points, i.position) for i in o.items], id=o.id,
    )


def to_attempt(o: AttemptORM) -> Attempt:
    return Attempt(o.exam_id, o.user_id, o.started_at, o.deadline, o.submitted_at, o.score, o.auto_submitted, o.id)
