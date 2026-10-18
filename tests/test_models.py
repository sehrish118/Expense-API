from sqlalchemy import Numeric

from app.db.base import Base


def test_all_tables_registered():
    assert set(Base.metadata.tables) == {
        "users",
        "refresh_tokens",
        "categories",
        "expenses",
        "budgets",
    }


def test_money_columns_use_numeric_not_float():
    tables = Base.metadata.tables
    for table, column in [("expenses", "amount"), ("budgets", "limit_amount")]:
        col_type = tables[table].c[column].type
        assert isinstance(col_type, Numeric)
        assert (col_type.precision, col_type.scale) == (12, 2)


def test_expenses_indexes_exist():
    names = {index.name for index in Base.metadata.tables["expenses"].indexes}
    assert {"ix_expenses_user_spent_at", "ix_expenses_user_category"} <= names
