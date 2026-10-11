"""Composition root: nơi duy nhất lắp ghép cài đặt cụ thể (infrastructure) vào use case (application)."""
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.application.dto import AttemptPolicy
from app.application.use_cases.attempts import (
    GetAttempt,
    GetAttemptResult,
    ListMyAttempts,
    SaveAnswers,
    StartAttempt,
    SubmitAttempt,
)
from app.application.use_cases.auth import Authenticate, Login, RegisterStudent
from app.application.use_cases.exams import CreateExam, ExamResults, GetExamDetail, ListExams, PublishExam
from app.application.use_cases.questions import CreateQuestion, DeleteQuestion, GetQuestion, SearchQuestions
from app.application.use_cases.users import CreateUser, ListUsers
from app.domain import rules
from app.domain.entities import ROLE_ADMIN, ROLE_STUDENT, ROLE_TEACHER, User
from app.domain.repositories import UnitOfWork
from app.infrastructure.cache.ttl_cache import TTLCache
from app.infrastructure.clock import SystemClock
from app.infrastructure.config import settings
from app.infrastructure.db.engine import SessionLocal
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.rate_limit import LoginRateLimiter
from app.infrastructure.security.jwt_service import JwtTokenService
from app.infrastructure.security.scrypt_hasher import ScryptHasher

# ---- Dịch vụ dùng chung (mỗi tiến trình một bản) -----------------------------------------------------
hasher = ScryptHasher()
tokens = JwtTokenService(settings.secret_key, settings.jwt_algorithm, settings.token_expire_minutes)
clock = SystemClock()
exam_cache = TTLCache()
login_rate_limiter = LoginRateLimiter(settings)
attempt_policy = AttemptPolicy(settings.cache_enabled, settings.cache_ttl_seconds, settings.submit_grace_seconds)


def uow_factory() -> SqlAlchemyUnitOfWork:
    """Dùng cho ngoài request (vòng quét nền, WebSocket) - nơi không có Depends."""
    return SqlAlchemyUnitOfWork(SessionLocal)


async def get_uow() -> AsyncIterator[UnitOfWork]:
    """Mỗi request một Unit of Work, tự đóng khi xong."""
    async with uow_factory() as uow:
        yield uow


UowDep = Annotated[UnitOfWork, Depends(get_uow)]


# ---- Xác thực và phân quyền ----------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], uow: UowDep) -> User:
    return await Authenticate(uow, tokens).execute(token)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    """Dependency factory: chỉ cho phép các vai trò được liệt kê."""

    async def checker(user: CurrentUser) -> User:
        rules.ensure_role(user, *roles)
        return user

    return checker


Teacher = Annotated[User, Depends(require_roles(ROLE_TEACHER, ROLE_ADMIN))]
Admin = Annotated[User, Depends(require_roles(ROLE_ADMIN))]
Student = Annotated[User, Depends(require_roles(ROLE_STUDENT))]


async def login_rate_limit(request: Request) -> None:
    login_rate_limiter.check(request.client.host if request.client else "unknown")


# ---- Use case: mỗi hàm lắp một use case với Unit of Work của request ----------------------------------
def _register_student(uow: UowDep) -> RegisterStudent:
    return RegisterStudent(uow, hasher)


def _login(uow: UowDep) -> Login:
    return Login(uow, hasher, tokens)


def _list_users(uow: UowDep) -> ListUsers:
    return ListUsers(uow)


def _create_user(uow: UowDep) -> CreateUser:
    return CreateUser(uow, hasher)


def _create_question(uow: UowDep) -> CreateQuestion:
    return CreateQuestion(uow)


def _search_questions(uow: UowDep) -> SearchQuestions:
    return SearchQuestions(uow)


def _get_question(uow: UowDep) -> GetQuestion:
    return GetQuestion(uow)


def _delete_question(uow: UowDep) -> DeleteQuestion:
    return DeleteQuestion(uow)


def _create_exam(uow: UowDep) -> CreateExam:
    return CreateExam(uow)


def _list_exams(uow: UowDep) -> ListExams:
    return ListExams(uow)


def _get_exam_detail(uow: UowDep) -> GetExamDetail:
    return GetExamDetail(uow)


def _publish_exam(uow: UowDep) -> PublishExam:
    return PublishExam(uow, exam_cache, clock)


def _exam_results(uow: UowDep) -> ExamResults:
    return ExamResults(uow)


def _start_attempt(uow: UowDep) -> StartAttempt:
    return StartAttempt(uow, exam_cache, clock, attempt_policy)


def _get_attempt(uow: UowDep) -> GetAttempt:
    return GetAttempt(uow, exam_cache, clock, attempt_policy)


def _list_my_attempts(uow: UowDep) -> ListMyAttempts:
    return ListMyAttempts(uow, clock)


def _save_answers(uow: UowDep) -> SaveAnswers:
    return SaveAnswers(uow, clock, attempt_policy)


def _submit_attempt(uow: UowDep) -> SubmitAttempt:
    return SubmitAttempt(uow, clock)


def _get_attempt_result(uow: UowDep) -> GetAttemptResult:
    return GetAttemptResult(uow, clock)


RegisterStudentDep = Annotated[RegisterStudent, Depends(_register_student)]
LoginDep = Annotated[Login, Depends(_login)]
ListUsersDep = Annotated[ListUsers, Depends(_list_users)]
CreateUserDep = Annotated[CreateUser, Depends(_create_user)]
CreateQuestionDep = Annotated[CreateQuestion, Depends(_create_question)]
SearchQuestionsDep = Annotated[SearchQuestions, Depends(_search_questions)]
GetQuestionDep = Annotated[GetQuestion, Depends(_get_question)]
DeleteQuestionDep = Annotated[DeleteQuestion, Depends(_delete_question)]
CreateExamDep = Annotated[CreateExam, Depends(_create_exam)]
ListExamsDep = Annotated[ListExams, Depends(_list_exams)]
GetExamDetailDep = Annotated[GetExamDetail, Depends(_get_exam_detail)]
PublishExamDep = Annotated[PublishExam, Depends(_publish_exam)]
ExamResultsDep = Annotated[ExamResults, Depends(_exam_results)]
StartAttemptDep = Annotated[StartAttempt, Depends(_start_attempt)]
GetAttemptDep = Annotated[GetAttempt, Depends(_get_attempt)]
ListMyAttemptsDep = Annotated[ListMyAttempts, Depends(_list_my_attempts)]
SaveAnswersDep = Annotated[SaveAnswers, Depends(_save_answers)]
SubmitAttemptDep = Annotated[SubmitAttempt, Depends(_submit_attempt)]
GetAttemptResultDep = Annotated[GetAttemptResult, Depends(_get_attempt_result)]
