from httpx import AsyncClient


async def test_health(async_client: AsyncClient) -> None:
    response = await async_client.get('/health')
    assert response.status_code == 200

    response = await async_client.get('/healthz')
    assert response.status_code == 200
