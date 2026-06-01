import pytest
from backend.db.engine import get_engine
from sqlalchemy import Engine, text
from sqlalchemy.orm.session import Session


@pytest.mark.usefixtures('needs_env_vars', 'database')
def test_get_engine() -> None:
    engine = get_engine()
    assert isinstance(engine, Engine)

    with Session(engine) as session:
        sql = 'SELECT 1 AS result'
        result = session.connection().execute(text(sql)).scalar()
        assert result == 1
