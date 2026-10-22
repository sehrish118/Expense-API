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


class InvalidRefreshTokenError(AppError):
    status_code = 401
    code = "invalid_refresh_token"
    default_message = "Invalid or expired refresh token"


class ForbiddenError(AppError):
    status_code = 403
    code = "Forbidden"
    default_message = "You do not have permission to do this"


class UserNotFoundError(AppError):
    status_code = 404
    code = "user_not_found"
    default_message = "User not found"


class CannotDeactivateSelfError(AppError):
    status_code = 400
    code = "cannot_deactivate_self"
    default_message = "You cannot deactivate your own account"


class CannotactivateSelfError(AppError):
    status_code = 400
    code = "cannot_activate_self"
    default_message = "You cannot activate your own account"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
            headers=headers,
        )
