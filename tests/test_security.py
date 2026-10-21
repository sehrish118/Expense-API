import base64
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def _unb64(part: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


# ---------- password hashing ----------


def test_hash_is_not_the_plain_password():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert hashed.startswith("$argon2")


def test_same_password_gives_different_hashes_because_of_salt():
    assert hash_password("secret123") != hash_password("secret123")


def test_verify_password_correct_and_wrong():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_with_garbage_hash_returns_false():
    assert verify_password("secret123", "not-a-real-hash") is False


# ---------- JWT ----------


def test_access_token_roundtrip():
    token = create_access_token("user_5")
    payload = decode_access_token(token)
    assert payload["sub"] == "user_5"
    assert payload["type"] == "access"


def test_payload_is_readable_by_anyone_not_encrypted():
    token = create_access_token("user_5")
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["sub"] == "user_5"


def test_expired_token_is_rejected():
    token = create_access_token("user_5", expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_payload_is_rejected():
    token = create_access_token("user_5")
    header, payload, signature = token.split(".")
    claims = _unb64(payload)
    claims["sub"] = "someone_else"
    forged = ".".join([header, _b64(claims), signature])
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_token_signed_with_other_secret_is_rejected():
    payload = {"sub": "user_5", "type": "access", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = jwt.encode(payload, "some-other-secret-key-0123456789abcdef", algorithm="HS256")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)


def test_non_access_token_type_is_rejected():
    payload = {"sub": "user_5", "type": "refresh", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_token_without_exp_is_rejected():
    token = jwt.encode(
        {"sub": "user_5", "type": "access"}, settings.jwt_secret_key, algorithm="HS256"
    )
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)


# --------------Refresh Tokens---------------
def test_refresh_tokens_are_random_and_unique():
    token = {generate_refresh_token() for _ in range(100)}
    assert len(token) == 100


def test_refresh_token_is_long_enough():
    assert len(generate_refresh_token()) >= 43


def test_refresh_token_hash_is_deterministic_64_hex_chars():
    token = generate_refresh_token()
    hashed = hash_refresh_token(token)
    assert hashed == hash_refresh_token(token)
    assert len(hashed) == 64
    assert all(c in "0123456789abcdef" for c in hashed)


def test_refresh_token_hash_differs_from_token_and_between_tokens():
    a, b = generate_refresh_token(), generate_refresh_token()
    assert hash_refresh_token(a) != a
    assert hash_refresh_token(a) != hash_refresh_token(b)
