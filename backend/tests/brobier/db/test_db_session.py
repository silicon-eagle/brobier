import pytest
from brobier.db.engine import get_admin_engine, get_engine
from sqlalchemy import Engine, text
from sqlalchemy.orm.session import Session


@pytest.mark.usefixtures('needs_env_vars', 'database')
def test_get_engine() -> None:
    engine = get_engine()
    admin_engine = get_admin_engine()
    assert isinstance(engine, Engine)
    assert isinstance(admin_engine, Engine)
    assert engine != admin_engine

    with Session(engine) as session:
        sql = 'SELECT 1 AS result'
        result = session.connection().execute(text(sql)).scalar()
        assert result == 1
