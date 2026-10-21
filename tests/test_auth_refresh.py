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
