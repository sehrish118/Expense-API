from pydantic import BaseModel

from app.schemas.user import Email


class LoginRequest(BaseModel):
    email: Email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
