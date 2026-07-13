"""Единый маппинг исключений → HTTP-ответ формата §6 (роутеры кодов не назначают)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import (
    Conflict,
    DomainError,
    DomainRuleViolation,
    NotFound,
    Unauthorized,
    ValidationError,
)

_STATUS = (
    (ValidationError, 400),
    (Unauthorized, 401),
    (NotFound, 404),
    (Conflict, 409),
    (DomainRuleViolation, 422),
)
_HTTP_CODES = {401: "UNAUTHORIZED", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def register(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError):
        status = next(s for cls, s in _STATUS if isinstance(exc, cls))
        return _error(status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        first = exc.errors()[0]
        loc = ".".join(str(part) for part in first["loc"] if part != "body")
        return _error(400, "VALIDATION", f"{loc}: {first['msg']}")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        return _error(exc.status_code, code, str(exc.detail))
