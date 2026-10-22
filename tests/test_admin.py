import uuid


async def test_admin_endpoint_without_token_returns_401(client):
    resp = await client.get("/admin/users")
    assert resp.status_code == 401


async def test_normal_user_gets_403_on_admin_endpoint(client, auth_headers):
    resp = await client.get("/admin/users", headers=auth_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "Forbidden"


async def test_admin_can_list_users_without_password_hashes(
    client, test_user, admin_user, admin_headers
):
    resp = await client.get("/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert {u["email"] for u in users} == {test_user.email, admin_user.email}
    assert all("hashed_password" not in u for u in users)


async def test_list_users_respects_limit(client, test_user, admin_user, admin_headers):
    resp = await client.get("/admin/users?limit=1", headers=admin_headers)
    assert len(resp.json()) == 1


async def test_list_users_rejects_bad_limit(client, admin_headers):
    resp = await client.get("/admin/users?limit=1000", headers=admin_headers)
    assert resp.status_code == 422


async def test_demoted_admin_loses_access_immediately(
    client, db_session, admin_user, admin_headers
):
    assert (await client.get("/admin/users", headers=admin_headers)).status_code == 200

    admin_user.role = "user"
    await db_session.commit()

    assert (await client.get("/admin/users", headers=admin_headers)).status_code == 403


async def test_normal_user_cannot_deactivate_anyone(client, test_user, admin_user, auth_headers):
    resp = await client.patch(f"/admin/users/{admin_user.id}/deactivate", headers=auth_headers)
    assert resp.status_code == 403


async def test_admin_can_deactivate_user(client, test_user, admin_headers):
    resp = await client.patch(f"/admin/users/{test_user.id}/deactivate", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_deactivated_user_loses_access_token_and_refresh_token(
    client, test_user, credentials, admin_headers
):
    tokens = (await client.post("/auth/login", json=credentials)).json()
    user_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert (await client.get("/auth/me", headers=user_headers)).status_code == 200

    await client.patch(f"/admin/users/{test_user.id}/deactivate", headers=admin_headers)

    assert (await client.get("/auth/me", headers=user_headers)).status_code == 401
    refresh = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401
    login = await client.post("/auth/login", json=credentials)
    assert login.status_code == 403


async def test_deactivate_is_idempotent(client, test_user, admin_headers):
    url = f"/admin/users/{test_user.id}/deactivate"
    assert (await client.patch(url, headers=admin_headers)).status_code == 200
    assert (await client.patch(url, headers=admin_headers)).status_code == 200


async def test_admin_cannot_deactivate_self(client, admin_user, admin_headers):
    resp = await client.patch(f"/admin/users/{admin_user.id}/deactivate", headers=admin_headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "cannot_deactivate_self"


async def test_deactivate_unknown_user_returns_404(client, admin_headers):
    resp = await client.patch(f"/admin/users/{uuid.uuid4()}/deactivate", headers=admin_headers)
    assert resp.status_code == 404


async def test_deactivate_with_invalid_uuid_returns_422(client, admin_headers):
    resp = await client.patch("/admin/users/not-a-uuid/deactivate", headers=admin_headers)
    assert resp.status_code == 422


async def test_register_cannot_set_role_mass_assignment(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "sneaky@example.com", "password": "password123", "role": "admin"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "user"
