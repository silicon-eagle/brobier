import pytest
from brobier.schemas.leaderboard import LeaderboardEntry
from httpx import AsyncClient


@pytest.mark.usefixtures('database')
class TestLeaderboardRoutes:
    async def test_get_leaderboard_without_year_uses_default(self, async_client: AsyncClient) -> None:
        response = await async_client.get('/leaderboard')
        assert response.status_code == 200
        models = [LeaderboardEntry.model_validate(item) for item in response.json()]
        assert all(isinstance(model, LeaderboardEntry) for model in models)
        assert all(model.display_name != 'Admin' for model in models)
