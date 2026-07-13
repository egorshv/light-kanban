"""Доменные исключения (ADR-006). Сервисный слой не знает про HTTP —
маппинг на статус-коды делает app/api/errors.py."""


class DomainError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ValidationError(DomainError):  # -> 400
    def __init__(self, message: str, code: str = "VALIDATION"):
        super().__init__(code, message)


class Unauthorized(DomainError):  # -> 401
    def __init__(self, message: str = "Требуется аутентификация", code: str = "UNAUTHORIZED"):
        super().__init__(code, message)


class NotFound(DomainError):  # -> 404
    def __init__(self, message: str, code: str = "NOT_FOUND"):
        super().__init__(code, message)


class Conflict(DomainError):  # -> 409
    def __init__(self, message: str, code: str = "CONFLICT"):
        super().__init__(code, message)


class DomainRuleViolation(DomainError):  # -> 422
    pass
