from collections.abc import Callable, Generator

import pytest
from brobier.auth.jwt import create_access_token
from brobier.core.security import encrypt_field
from brobier.core.time import current_time
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, CalendarEntry, User
from brobier.schemas.admin import AdminCalendarEntryOut
from brobier.seeds.seed import _get_seed_years
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session


def _token_for(email: str) -> str:
    with Session(get_app_engine()) as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
    return create_access_token(user.id, user.role)


@pytest.fixture
def admin_token(database: None) -> str:  # noqa: ARG001
    return _token_for('admin@brobier.local')


@pytest.fixture
def alice_token(database: None) -> str:  # noqa: ARG001
    return _token_for('alice@brobier.local')


@pytest.fixture
def make_beer_entry_id(database: None) -> Generator[Callable[[int], int]]:  # noqa: ARG001
    created_ids: list[int] = []

    def create(year: int) -> int:
        with Session(get_app_engine()) as db:
            user: User | None = db.scalar(select(User).where(User.email == 'alice@brobier.local'))
            assert user is not None
            beer = BeerEntry(
                user_id=user.id,
                year=year,
                beer_name_encrypted=encrypt_field('Admin Calendar Test Beer'),
                brewery_encrypted=encrypt_field('Admin Calendar Brewery'),
                untappd_url_encrypted=None,
                comment_encrypted=None,
                bought_from='Admin Calendar Shop',
                bought_at=current_time(),
            )
            db.add(beer)
            db.commit()
            db.refresh(beer)
            created_ids.append(beer.id)
            return beer.id

    yield create

    with Session(get_app_engine()) as db:
        linked_entries = db.scalars(select(CalendarEntry).where(CalendarEntry.beer_entry_id.in_(created_ids))).all()
        for entry in linked_entries:
            entry.beer_entry_id = None
        for beer_id in created_ids:
            beer = db.scalar(select(BeerEntry).where(BeerEntry.id == beer_id))
            if beer:
                db.delete(beer)
        db.commit()


@pytest.mark.usefixtures('database')
class TestAdminCalendar:
    async def test_list_calendar(self, async_client: AsyncClient, admin_token: str) -> None:
        year = _get_seed_years()[0]

        response = await async_client.get('/admin/calendar', params={'year': year}, headers={'Authorization': f'Bearer {admin_token}'})

        assert response.status_code == 200
        entries = [AdminCalendarEntryOut.model_validate(item) for item in response.json()]
        assert len(entries) == 24
        assert [entry.day for entry in entries] == list(range(1, 25))
        assert all(entry.year == year for entry in entries)

    async def test_list_calendar_requires_admin(self, async_client: AsyncClient, alice_token: str) -> None:
        user_response = await async_client.get('/admin/calendar', headers={'Authorization': f'Bearer {alice_token}'})
        missing_token_response = await async_client.get('/admin/calendar')

        assert user_response.status_code == 403
        assert missing_token_response.status_code == 401

    async def test_create_calendar_year(self, async_client: AsyncClient, admin_token: str) -> None:
        year = current_time().year + 20
        headers = {'Authorization': f'Bearer {admin_token}'}

        response = await async_client.put(f'/admin/calendar/{year}', headers=headers)

        assert response.status_code == 204
        calendar = await async_client.get('/admin/calendar', params={'year': year}, headers=headers)
        entries = [AdminCalendarEntryOut.model_validate(item) for item in calendar.json()]
        assert len(entries) == 24
        assert [entry.day for entry in entries] == list(range(1, 25))

    async def test_delete_calendar_year(self, async_client: AsyncClient, admin_token: str) -> None:
        year = current_time().year + 21
        headers = {'Authorization': f'Bearer {admin_token}'}
        create_response = await async_client.put(f'/admin/calendar/{year}', headers=headers)
        assert create_response.status_code == 204

        response = await async_client.delete(f'/admin/calendar/{year}', headers=headers)

        assert response.status_code == 204
        calendar = await async_client.get('/admin/calendar', params={'year': year}, headers=headers)
        assert calendar.json() == []

    async def test_assign_beer(self, async_client: AsyncClient, admin_token: str, make_beer_entry_id: Callable[[int], int]) -> None:
        year = _get_seed_years()[0]
        beer_entry_id = make_beer_entry_id(year)

        response = await async_client.put(
            f'/admin/calendar/{year}/1/beer',
            json={'beer_entry_id': beer_entry_id},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert response.status_code == 200
        entry = AdminCalendarEntryOut.model_validate(response.json())
        assert entry.beer_entry_id == beer_entry_id
        assert entry.beer is not None
        assert entry.beer.beer_name == 'Admin Calendar Test Beer'
        assert entry.beer.display_name == 'Alice'

        calendar = await async_client.get('/admin/calendar', params={'year': year}, headers={'Authorization': f'Bearer {admin_token}'})
        assert calendar.status_code == 200
        entries = [AdminCalendarEntryOut.model_validate(item) for item in calendar.json()]
        assert len(entries) == 24
        assigned = [entry for entry in entries if entry.beer_entry_id is not None]
        assert len(assigned) == 1
        assert assigned[0].beer_entry_id == beer_entry_id

    async def test_unassign_beer(self, async_client: AsyncClient, admin_token: str, make_beer_entry_id: Callable[[int], int]) -> None:
        year = _get_seed_years()[0]
        beer_entry_id = make_beer_entry_id(year)
        headers = {'Authorization': f'Bearer {admin_token}'}
        payload = {'beer_entry_id': beer_entry_id}
        assign_response = await async_client.put(f'/admin/calendar/{year}/2/beer', json=payload, headers=headers)
        assert assign_response.status_code == 200

        response = await async_client.delete(f'/admin/calendar/{year}/2/beer', headers=headers)

        assert response.status_code == 200
        entry = AdminCalendarEntryOut.model_validate(response.json())
        assert entry.beer_entry_id is None
        assert entry.beer is None

    async def test_assign_beer_returns_not_found(
        self,
        async_client: AsyncClient,
        admin_token: str,
        make_beer_entry_id: Callable[[int], int],
    ) -> None:
        year = _get_seed_years()[0]
        beer_entry_id = make_beer_entry_id(year)
        headers = {'Authorization': f'Bearer {admin_token}'}

        missing_day = await async_client.put('/admin/calendar/9999/1/beer', json={'beer_entry_id': beer_entry_id}, headers=headers)
        missing_beer = await async_client.put(f'/admin/calendar/{year}/1/beer', json={'beer_entry_id': 999999}, headers=headers)

        assert missing_day.status_code == 404
        assert missing_beer.status_code == 404

    async def test_assign_beer_returns_conflict(
        self,
        async_client: AsyncClient,
        admin_token: str,
        make_beer_entry_id: Callable[[int], int],
    ) -> None:
        year = _get_seed_years()[0]
        beer_entry_id = make_beer_entry_id(year)
        headers = {'Authorization': f'Bearer {admin_token}'}
        payload = {'beer_entry_id': beer_entry_id}
        assign_response = await async_client.put(f'/admin/calendar/{year}/3/beer', json=payload, headers=headers)
        assert assign_response.status_code == 200

        response = await async_client.put(f'/admin/calendar/{year}/4/beer', json=payload, headers=headers)

        assert response.status_code == 409

    async def test_assign_beer_returns_conflict_for_different_year(
        self,
        async_client: AsyncClient,
        admin_token: str,
        make_beer_entry_id: Callable[[int], int],
    ) -> None:
        year = _get_seed_years()[0]
        beer_entry_id = make_beer_entry_id(year + 1)

        response = await async_client.put(
            f'/admin/calendar/{year}/4/beer',
            json={'beer_entry_id': beer_entry_id},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert response.status_code == 409
        assert response.json()['detail'] == 'Beer entry belongs to a different calendar year.'

    async def test_delete_calendar_year_returns_conflict(
        self,
        async_client: AsyncClient,
        admin_token: str,
        make_beer_entry_id: Callable[[int], int],
    ) -> None:
        year = current_time().year + 22
        beer_entry_id = make_beer_entry_id(year)
        headers = {'Authorization': f'Bearer {admin_token}'}
        create_response = await async_client.put(f'/admin/calendar/{year}', headers=headers)
        assert create_response.status_code == 204
        assign_response = await async_client.put(
            f'/admin/calendar/{year}/6/beer',
            json={'beer_entry_id': beer_entry_id},
            headers=headers,
        )
        assert assign_response.status_code == 200

        response = await async_client.delete(f'/admin/calendar/{year}', headers=headers)

        assert response.status_code == 409
        assert response.json()['detail'] == 'Cannot delete calendar year because at least one day has an assigned beer.'

    async def test_delete_assigned_beer_returns_conflict(
        self,
        async_client: AsyncClient,
        admin_token: str,
        alice_token: str,
        make_beer_entry_id: Callable[[int], int],
    ) -> None:
        year = _get_seed_years()[0]
        beer_entry_id = make_beer_entry_id(year)
        assign_response = await async_client.put(
            f'/admin/calendar/{year}/5/beer',
            json={'beer_entry_id': beer_entry_id},
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert assign_response.status_code == 200

        response = await async_client.delete(f'/beers/{beer_entry_id}', headers={'Authorization': f'Bearer {alice_token}'})

        assert response.status_code == 409
        assert response.json()['detail'] == 'Cannot delete beer assigned to a calendar day.'

    async def test_unassign_beer_returns_not_found(self, async_client: AsyncClient, admin_token: str) -> None:
        response = await async_client.delete('/admin/calendar/9999/1/beer', headers={'Authorization': f'Bearer {admin_token}'})

        assert response.status_code == 404
