"""Typed application errors that carry their own HTTP status code.

Services raise these instead of plain ``ValueError``/``PermissionError`` so the
API layer can map them to HTTP responses by type, rather than by matching on the
error message text. A single exception handler (registered in ``main.py``) turns
any ``AppError`` into a JSON response using its ``status_code`` and ``detail``.

``UnauthorizedError``/``NotFoundError``/``ConflictError`` subclass ``ValueError``
and ``ForbiddenError`` subclasses ``PermissionError`` so existing callers and
tests that catch the builtin types keep working.
"""


class AppError(Exception):
    status_code: int = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError, ValueError):
    status_code = 404


class ConflictError(AppError, ValueError):
    status_code = 409


class ForbiddenError(AppError, PermissionError):
    status_code = 403


class UnauthorizedError(AppError, ValueError):
    status_code = 401
