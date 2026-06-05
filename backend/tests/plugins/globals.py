import pytest


@pytest.fixture(scope='session', autouse=True)
def tst_globals() -> dict[str, str]:
    return {
        'USER': 'alice@brobier.local',
        'ADMIN': 'admin@brobier.local',
    }
