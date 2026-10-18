from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    default_message = "Something went wrong"

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class EmailAlreadyRegisteredError(AppError):
    status_code = 409
    code = "email_already_registered"
    default_message = "Email already registered"


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "invalid_credentials"
    default_message = "Invalid email or password"


class InactiveUserError(AppError):
    status_code = 403
    code = "inactive_user"
    default_message = "This account is disabled"


class NotAuthenticatedError(AppError):
    status_code = 401
    code = "not_authenticated"
    default_message = "Not authenticated"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
            headers=headers,
        )
