from sqlalchemy import inspect, text

EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "categories",
    "expenses",
    "budgets",
    "alembic_version",
}


async def test_db_conection(engine):
    async with engine.connect() as conn:
        result = await conn.execute(text("select 1"))
        assert result.scalar() == 1


async def test_migrations_created_all_tables(engine):
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))

    assert EXPECTED_TABLES <= tables
