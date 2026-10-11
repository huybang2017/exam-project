"""Cài đặt giả trong bộ nhớ cho các port/repository: test use case không cần DB, HTTP hay đồng hồ thật."""
import copy
from datetime import datetime, timedelta

from app.domain.entities import (
    ROLE_ADMIN,
    ROLE_STUDENT,
    ROLE_TEACHER,
    Attempt,
    Exam,
    ExamResultRow,
    GradeInputs,
    PublicChoice,
    PublicQuestion,
    Question,
    User,
)
from app.domain.errors import ConflictError, DuplicateAttemptError, UnauthorizedError
from app.domain.ports import TokenPayload


class FakeClock:
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 10, 10, 8, 0, 0)

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        self._now += timedelta(**kwargs)


class FakeHasher:
    async def hash(self, password: str) -> str:
        return f"hashed:{password}"

    async def verify(self, password: str, stored: str | None) -> bool:
        return stored is not None and stored == f"hashed:{password}"


class FakeTokens:
    def create(self, user_id: int, role: str) -> str:
        return f"token-{user_id}-{role}"

    def decode(self, token: str) -> TokenPayload:
        try:
            _, uid, role = token.split("-")
            return TokenPayload(int(uid), role)
        except ValueError:
            raise UnauthorizedError("Token không hợp lệ hoặc đã hết hạn")


class FakeCache:
    def __init__(self) -> None:
        self.data: dict = {}
        self.sets = 0

    def get(self, exam_id):
        return self.data.get(exam_id)

    def set(self, exam_id, questions, ttl) -> None:
        self.data[exam_id] = questions
        self.sets += 1

    def invalidate(self, exam_id) -> None:
        self.data.pop(exam_id, None)


class _Store:
    """Kho dữ liệu dùng chung cho các repository giả (mô phỏng một CSDL)."""

    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.questions: dict[int, Question] = {}
        self.exams: dict[int, Exam] = {}
        self.attempts: dict[int, Attempt] = {}
        self.answers: dict[int, dict[int, int]] = {}
        self.next_id = 1

    def new_id(self) -> int:
        self.next_id += 1
        return self.next_id - 1


class FakeUsers:
    def __init__(self, s: _Store) -> None:
        self.s = s

    async def get(self, user_id):
        return copy.deepcopy(self.s.users.get(user_id))

    async def get_by_username(self, username):
        return next((copy.deepcopy(u) for u in self.s.users.values() if u.username == username), None)

    async def add(self, user):
        if any(u.username == user.username for u in self.s.users.values()):
            raise ConflictError("Tên đăng nhập đã tồn tại")
        user = copy.deepcopy(user)
        user.id = self.s.new_id()
        self.s.users[user.id] = user
        return copy.deepcopy(user)

    async def list(self, role, skip, limit):
        items = [u for u in self.s.users.values() if role is None or u.role == role]
        return len(items), copy.deepcopy(items[skip: skip + limit])

    async def count(self):
        return len(self.s.users)


class FakeQuestions:
    def __init__(self, s: _Store) -> None:
        self.s = s

    async def add(self, question):
        question = copy.deepcopy(question)
        question.id = self.s.new_id()
        for c in question.choices:
            c.id = self.s.new_id()
        self.s.questions[question.id] = question
        return copy.deepcopy(question)

    async def get(self, question_id):
        return copy.deepcopy(self.s.questions.get(question_id))

    async def search(self, text, skip, limit):
        items = [q for q in self.s.questions.values() if not text or text.lower() in q.content.lower()]
        return len(items), copy.deepcopy(items[skip: skip + limit])

    async def delete(self, question_id):
        self.s.questions.pop(question_id, None)

    async def is_used_in_exam(self, question_id):
        return any(i.question_id == question_id for e in self.s.exams.values() for i in e.items)

    async def count_existing(self, question_ids):
        return sum(1 for q in question_ids if q in self.s.questions)


class FakeExams:
    def __init__(self, s: _Store) -> None:
        self.s = s

    async def add(self, exam):
        exam = copy.deepcopy(exam)
        exam.id = self.s.new_id()
        self.s.exams[exam.id] = exam
        return copy.deepcopy(exam)

    async def get(self, exam_id):
        return copy.deepcopy(self.s.exams.get(exam_id))

    async def list_for(self, user):
        exams = list(self.s.exams.values())
        if user.role == ROLE_STUDENT:
            exams = [e for e in exams if e.is_published]
        elif user.role == ROLE_TEACHER:
            exams = [e for e in exams if e.owner_id == user.id]
        return copy.deepcopy(exams)

    async def save(self, exam):
        self.s.exams[exam.id] = copy.deepcopy(exam)

    async def questions_with_answers(self, exam_id):
        exam = self.s.exams[exam_id]
        return copy.deepcopy([self.s.questions[i.question_id] for i in exam.items])

    async def public_questions(self, exam_id):
        exam = self.s.exams[exam_id]
        out = []
        for item in exam.items:
            q = self.s.questions[item.question_id]
            out.append(PublicQuestion(q.id, q.content, item.points,
                                      tuple(PublicChoice(c.id, c.text) for c in q.choices)))
        return tuple(out)

    async def valid_choice_pairs(self, exam_id, choice_ids):
        exam = self.s.exams[exam_id]
        pairs = set()
        for item in exam.items:
            for c in self.s.questions[item.question_id].choices:
                if c.id in choice_ids:
                    pairs.add((c.id, item.question_id))
        return pairs


class FakeAttempts:
    def __init__(self, s: _Store) -> None:
        self.s = s
        self.race_for: tuple[int, int] | None = None  # (exam_id, user_id): mô phỏng request khác chen vào trước

    async def add(self, attempt):
        if self.race_for == (attempt.exam_id, attempt.user_id):
            self.race_for = None
            other = copy.deepcopy(attempt)
            other.id = self.s.new_id()
            self.s.attempts[other.id] = other
            raise DuplicateAttemptError()
        if any(a.exam_id == attempt.exam_id and a.user_id == attempt.user_id for a in self.s.attempts.values()):
            raise DuplicateAttemptError()
        attempt = copy.deepcopy(attempt)
        attempt.id = self.s.new_id()
        self.s.attempts[attempt.id] = attempt
        return copy.deepcopy(attempt)

    async def get(self, attempt_id):
        return copy.deepcopy(self.s.attempts.get(attempt_id))

    async def get_for_exam_user(self, exam_id, user_id):
        return next((copy.deepcopy(a) for a in self.s.attempts.values()
                     if a.exam_id == exam_id and a.user_id == user_id), None)

    async def list_for_user(self, user_id):
        return copy.deepcopy([a for a in self.s.attempts.values() if a.user_id == user_id])

    async def save(self, attempt):
        self.s.attempts[attempt.id] = copy.deepcopy(attempt)

    async def saved_answers(self, attempt_id):
        return dict(self.s.answers.get(attempt_id, {}))

    async def upsert_answers(self, attempt_id, answers):
        self.s.answers.setdefault(attempt_id, {}).update(answers)

    async def grade_inputs(self, attempt):
        exam = self.s.exams[attempt.exam_id]
        points = {i.question_id: i.points for i in exam.items}
        earned, correct = 0.0, 0
        for qid, cid in self.s.answers.get(attempt.id, {}).items():
            q = self.s.questions[qid]
            if any(c.id == cid and c.is_correct for c in q.choices):
                earned += points[qid]
                correct += 1
        return GradeInputs(earned, correct, sum(points.values()), len(points))

    async def list_expired(self, now):
        return copy.deepcopy([a for a in self.s.attempts.values() if not a.is_submitted and a.deadline < now])

    async def results_for_exam(self, exam_id):
        rows = []
        for a in self.s.attempts.values():
            if a.exam_id == exam_id:
                u = self.s.users[a.user_id]
                rows.append(ExamResultRow(u.id, u.username, u.full_name, a.score, a.submitted_at, a.auto_submitted))
        return rows


class FakeUnitOfWork:
    def __init__(self) -> None:
        s = _Store()
        self.store = s
        self.users, self.questions = FakeUsers(s), FakeQuestions(s)
        self.exams, self.attempts = FakeExams(s), FakeAttempts(s)
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


def make_user(role: str, name: str, user_id: int) -> User:
    return User(name, name, role, f"hashed:{name}", user_id)


__all__ = ["FakeUnitOfWork", "FakeClock", "FakeHasher", "FakeTokens", "FakeCache", "make_user",
           "ROLE_ADMIN", "ROLE_STUDENT", "ROLE_TEACHER"]
