import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope='module')
def client(database: None) -> TestClient:
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
