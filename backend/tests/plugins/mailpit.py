from collections.abc import Generator

import httpx2
import pytest


@pytest.fixture(scope='session')
def mailpit() -> Generator[str]:
    mailpit_base = 'http://localhost:8025/api/v1'

    try:
        httpx2.get(f'{mailpit_base}/info', timeout=2).raise_for_status()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f'Mailpit is not reachable at {mailpit_base}: {e}')

    yield mailpit_base

    httpx2.request('DELETE', f'{mailpit_base}/messages').raise_for_status()
