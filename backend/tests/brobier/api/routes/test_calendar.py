import pytest
from brobier.api.routes.calendar import CalendarEntryOut
from brobier.auth.jwt import create_access_token
from brobier.db.engine import get_app_engine
from brobier.db.models import User
from brobier.schemas.calendar import YearOut
from brobier.seeds.seed import _get_seed_years
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def alice_token() -> str:
    with Session(get_app_engine()) as db:
        user = db.scalar(select(User).where(User.email == 'alice@brobier.local'))
        assert user is not None
    return create_access_token(user.id, user.role)


@pytest.mark.usefixtures('database')
class TestCalendarRoutes:
    async def test_get_years_with_user(self, async_client: AsyncClient, alice_token: str) -> None:
        response = await async_client.get('/calendar/years', headers={'Authorization': f'Bearer {alice_token}'})
        assert response.status_code == 200
        models = [YearOut.model_validate(item) for item in response.json()]
        assert all(isinstance(model, YearOut) for model in models)

    async def test_get_years_without_user(self, async_client: AsyncClient) -> None:
        response = await async_client.get('/calendar/years')
        assert response.status_code == 401

    async def test_get_years_invalid_token(self, async_client: AsyncClient) -> None:
        response = await async_client.get('/calendar/years', headers={'Authorization': 'Bearer invalid-token'})
        assert response.status_code == 401

    async def test_list_calendar(self, async_client: AsyncClient, alice_token: str) -> None:
        response = await async_client.get('/calendar', headers={'Authorization': f'Bearer {alice_token}'})
        assert response.status_code == 200
        days = [CalendarEntryOut.model_validate(item) for item in response.json()]
        assert all(isinstance(day, CalendarEntryOut) for day in days)

    async def test_list_calendar_without_user(self, async_client: AsyncClient) -> None:
        response = await async_client.get('/calendar')
        assert response.status_code == 401

    async def test_get_calendar_day_forbidden(self, async_client: AsyncClient, alice_token: str) -> None:
        year = _get_seed_years()[-1]
        response = await async_client.get(f'/calendar/{year}/1', headers={'Authorization': f'Bearer {alice_token}'})
        assert response.status_code == 403

    async def test_get_calendar_day(self, async_client: AsyncClient, alice_token: str) -> None:
        year = _get_seed_years()[0]
        response = await async_client.get(f'/calendar/{year}/1', headers={'Authorization': f'Bearer {alice_token}'})
        assert response.status_code == 200
        model = CalendarEntryOut.model_validate(response.json())
        assert isinstance(model, CalendarEntryOut)
