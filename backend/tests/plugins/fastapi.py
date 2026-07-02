from collections.abc import AsyncGenerator

import pytest_asyncio
from brobier.main import app
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture(scope='session', loop_scope='session')
async def async_client() -> AsyncGenerator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        yield client
