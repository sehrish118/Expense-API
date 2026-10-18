import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import text

from app.core.security import create_access_token

# ---------- register ----------


async def test_register_success(client):
    resp = await client.post(
        "/auth/register", json={"email": "Ali@Example.com", "password": "password123"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "ali@example.com"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "hashed_password" not in body
    assert "password" not in body


async def test_register_stores_hash_not_plain_password(client, db_session):
    await client.post(
        "/auth/register", json={"email": "ali@example.com", "password": "password123"}
    )
    stored = (
        await db_session.execute(
            text("select hashed_password from users where email = 'ali@example.com'")
        )
    ).scalar_one()
    assert stored != "password123"
    assert stored.startswith("$argon2")


async def test_register_duplicate_email_returns_409(client, test_user):
    resp = await client.post(
        "/auth/register",
        json={"email": test_user.email.upper(), "password": "password123"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_already_registered"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "password123"},
        {"email": "a@example.com", "password": "short"},
        {"email": "a@example.com"},
    ],
)
async def test_register_invalid_input_returns_422(client, payload):
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 422


# ---------- login ----------


async def test_login_success_and_token_works(client, test_user, credentials):
    resp = await client.post("/auth/login", json=credentials)
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == credentials["email"]


async def test_login_wrong_password_and_unknown_email_look_identical(
    client, test_user, credentials
):
    wrong_password = await client.post(
        "/auth/login", json={**credentials, "password": "wrong-password"}
    )
    unknown_email = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "password123"}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_login_inactive_user_returns_403(client, db_session, test_user, credentials):
    test_user.is_active = False
    await db_session.commit()

    resp = await client.post("/auth/login", json=credentials)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "inactive_user"


# ---------- /auth/me ----------


async def test_me_without_token_returns_401(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"
    assert resp.json()["error"]["code"] == "not_authenticated"


async def test_me_with_garbage_token_returns_401(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert resp.status_code == 401


async def test_me_with_expired_token_returns_401(client, test_user):
    token = create_access_token(str(test_user.id), expires_delta=timedelta(seconds=-1))
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_me_with_token_signed_by_wrong_key_returns_401(client, test_user):
    forged = jwt.encode(
        {
            "sub": str(test_user.id),
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "wrong-secret-key-0123456789abcdef0123",
        algorithm="HS256",
    )
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


async def test_me_with_valid_token_returns_user(client, test_user, auth_headers):
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(test_user.id)
    assert body["email"] == test_user.email
    assert "hashed_password" not in body


async def test_me_for_deactivated_user_returns_401_even_with_valid_token(
    client, db_session, test_user, auth_headers
):
    test_user.is_active = False
    await db_session.commit()

    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 401


async def test_me_with_token_of_unknown_user_returns_401(client):
    token = create_access_token(str(uuid.uuid4()))
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_me_with_non_uuid_subject_returns_401(client):
    token = create_access_token("not-a-uuid")
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
