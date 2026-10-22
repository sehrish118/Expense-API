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
