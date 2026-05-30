import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.db.engine import get_engine
from backend.db.session import get_db
from backend.main import app


@pytest.fixture(scope='module')
def client(database: None) -> TestClient:
    engine = get_engine()

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
