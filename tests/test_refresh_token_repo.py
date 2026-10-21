from datetime import UTC, datetime, timedelta

from app.core.security import generate_refresh_token, hash_refresh_token
from app.repositories.refresh_token import RefreshTokenRepository


def _expiry():
    return datetime.now(UTC) + timedelta(days=7)


def _new_hash():
    return hash_refresh_token(generate_refresh_token())


async def test_create_then_get_by_hash(db_session, test_user):
    repo = RefreshTokenRepository(db_session)
    token_hash = _new_hash()

    await repo.create(test_user.id, token_hash, _expiry())
    found = await repo.get_by_hash(token_hash)

    assert found is not None
    assert found.user_id == test_user.id
    assert found.revoked_at is None


async def test_get_by_hash_unknown_returns_none(db_session):
    repo = RefreshTokenRepository(db_session)
    assert await repo.get_by_hash("0" * 64) is None


async def test_revoke_sets_revoked_at(db_session, test_user):
    repo = RefreshTokenRepository(db_session)
    token = await repo.create(test_user.id, _new_hash(), _expiry())

    await repo.revoke(token)

    assert token.revoked_at is not None


async def test_revoke_all_only_touches_active_tokens(db_session, test_user):
    repo = RefreshTokenRepository(db_session)
    already_revoked = await repo.create(test_user.id, _new_hash(), _expiry())
    active = await repo.create(test_user.id, _new_hash(), _expiry())
    await repo.revoke(already_revoked)
    original_revoke_time = already_revoked.revoked_at

    await repo.revoke_all_for_user(test_user.id)
    await db_session.refresh(already_revoked)
    await db_session.refresh(active)

    assert active.revoked_at is not None
    assert already_revoked.revoked_at == original_revoke_time


async def _login(client, credentials) -> dict:
    resp = await client.post("/auth/login", json=credentials)
    assert resp.status_code == 200
    return resp.json()


async def _refresh(client, token: str):
    return await client.post("/auth/refresh", json={"refresh_token": token})


async def test_login_returns_access_and_refresh_token(client, test_user, credentials):
    tokens = await _login(client, credentials)
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


async def test_refresh_returns_new_pair_and_new_access_token_works(client, test_user, credentials):
    first = await _login(client, credentials)
    resp = await _refresh(client, first["refresh_token"])

    assert resp.status_code == 200
    second = resp.json()
    assert second["refresh_token"] != first["refresh_token"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {second['access_token']}"})
    assert me.status_code == 200


async def test_refresh_token_cannot_be_used_twice(client, test_user, credentials):
    first = await _login(client, credentials)
    assert (await _refresh(client, first["refresh_token"])).status_code == 200

    resp = await _refresh(client, first["refresh_token"])
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_refresh_token"


async def test_reuse_also_kills_the_newer_token(client, test_user, credentials):
    first = await _login(client, credentials)
    second = (await _refresh(client, first["refresh_token"])).json()

    await _refresh(client, first["refresh_token"])

    resp = await _refresh(client, second["refresh_token"])
    assert resp.status_code == 401


async def test_refresh_with_garbage_token_returns_401(client):
    resp = await _refresh(client, "garbage")
    assert resp.status_code == 401


async def test_refresh_without_body_returns_422(client):
    resp = await client.post("/auth/refresh", json={})
    assert resp.status_code == 422


async def test_access_token_is_not_accepted_as_refresh_token(client, test_user, credentials):
    tokens = await _login(client, credentials)
    resp = await _refresh(client, tokens["access_token"])
    assert resp.status_code == 401


async def test_logout_revokes_refresh_token(client, test_user, credentials):
    tokens = await _login(client, credentials)

    resp = await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 204
    assert resp.content == b""

    assert (await _refresh(client, tokens["refresh_token"])).status_code == 401


async def test_logout_is_idempotent(client, test_user, credentials):
    tokens = await _login(client, credentials)
    body = {"refresh_token": tokens["refresh_token"]}

    assert (await client.post("/auth/logout", json=body)).status_code == 204
    assert (await client.post("/auth/logout", json=body)).status_code == 204
    assert (
        await client.post("/auth/logout", json={"refresh_token": "never-issued"})
    ).status_code == 204


async def test_access_token_still_works_after_logout(client, test_user, credentials):
    tokens = await _login(client, credentials)
    await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
