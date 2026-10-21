from pydantic import BaseModel

from app.schemas.user import Email


class LoginRequest(BaseModel):
    email: Email
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
