import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserRead


def test_Email_is_lowercased():
    user = UserCreate(email="Sehrish@Example.COM", password="longenough1")
    assert user.email == "sehrish@example.com"


def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="longenough1")


def test_short_password_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="ali@example.com", password="short")


def test_very_long_password_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(email="ali@example.com", password="x" * 129)


def test_user_read_never_exposes_password_hash():
    assert "hashed_password" not in UserRead.model_fields
