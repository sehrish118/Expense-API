from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import InvalidRefreshTokenError
from app.core.security import generate_refresh_token, hash_refresh_token
from app.repositories.refresh_token import RefreshTokenRepository
from app.services.auth import AuthService


@pytest.fixture
def service(db_session):
    return AuthService(db_session)


async def test_login_returns_both_tokens_and_stores_only_the_hash(
    service, db_session, test_user, credentials
):
    tokens = await service.login(credentials["email"], credentials["password"])

    assert tokens.access_token
    assert tokens.refresh_token
    repo = RefreshTokenRepository(db_session)
    assert await repo.get_by_hash(tokens.refresh_token) is None
    assert await repo.get_by_hash(hash_refresh_token(tokens.refresh_token)) is not None


async def test_refresh_rotates_the_token(service, db_session, test_user, credentials):
    first = await service.login(credentials["email"], credentials["password"])
    second = await service.refresh(first.refresh_token)

    assert second.refresh_token != first.refresh_token
    old = await RefreshTokenRepository(db_session).get_by_hash(
        hash_refresh_token(first.refresh_token)
    )
    assert old.revoked_at is not None


async def test_reusing_a_refresh_token_fails(service, test_user, credentials):
    first = await service.login(credentials["email"], credentials["password"])
    await service.refresh(first.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(first.refresh_token)


async def test_reuse_revokes_all_tokens_of_that_user(service, test_user, credentials):
    first = await service.login(credentials["email"], credentials["password"])
    second = await service.refresh(first.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(first.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(second.refresh_token)


async def test_unknown_refresh_token_fails(service):
    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh("this-token-was-never-issued")


async def test_expired_refresh_token_fails(service, db_session, test_user):
    raw = generate_refresh_token()
    await RefreshTokenRepository(db_session).create(
        test_user.id, hash_refresh_token(raw), datetime.now(UTC) - timedelta(seconds=1)
    )

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(raw)


async def test_refresh_fails_for_deactivated_user(service, db_session, test_user, credentials):
    tokens = await service.login(credentials["email"], credentials["password"])
    test_user.is_active = False
    await db_session.commit()

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(tokens.refresh_token)


async def test_logout_revokes_refresh_token(service, test_user, credentials):
    tokens = await service.login(credentials["email"], credentials["password"])
    await service.logout(tokens.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(tokens.refresh_token)


async def test_logout_with_unknown_token_does_nothing(service):
    await service.logout("this-token-was-never-issued")
