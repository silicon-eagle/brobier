from collections.abc import AsyncGenerator

import pytest
from brobier.auth.jwt import create_access_token
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, User, UserRating
from brobier.schemas.admin import AdminBeerEntryOut
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

_ALICE_BEER_PAYLOAD = {
    'year': 2024,
    'beer_name': 'Admin Test Lager',
    'brewery': 'Admin Test Brewery',
    'bought_from': 'Admin Test Shop',
    'bought_at': '2024-12-01T12:00:00Z',
}

_BOB_BEER_PAYLOAD = {
    'year': 2025,
    'beer_name': 'Admin Test Porter',
    'brewery': 'Admin Test Dark Brewery',
    'bought_from': 'Admin Test Bottle Shop',
    'bought_at': '2025-12-02T12:00:00Z',
}


@pytest.fixture
def admin_token() -> str:
    with Session(get_app_engine()) as db:
        user: User | None = db.scalar(select(User).where(User.email == 'admin@brobier.local'))
        assert user is not None
    return create_access_token(user.id, user.role)


@pytest.fixture
def alice_token() -> str:
    with Session(get_app_engine()) as db:
        user: User | None = db.scalar(select(User).where(User.email == 'alice@brobier.local'))
        assert user is not None
    return create_access_token(user.id, user.role)


@pytest.fixture
def bob_token() -> str:
    with Session(get_app_engine()) as db:
        user: User | None = db.scalar(select(User).where(User.email == 'bob@brobier.local'))
        assert user is not None
    return create_access_token(user.id, user.role)


@pytest.fixture
async def admin_list_beers(
    async_client: AsyncClient,
    alice_token: str,
    bob_token: str,
) -> AsyncGenerator[list[dict]]:
    beers = []
    try:
        for payload, token in (
            (_ALICE_BEER_PAYLOAD, alice_token),
            (_BOB_BEER_PAYLOAD, bob_token),
        ):
            response = await async_client.post('/beers', json=payload, headers={'Authorization': f'Bearer {token}'})
            assert response.status_code == 201
            beers.append(response.json())

        yield beers
    finally:
        with Session(get_app_engine()) as db:
            for beer in beers:
                ratings = db.scalars(select(UserRating).where(UserRating.beer_entry_id == beer['id'])).all()
                for rating in ratings:
                    db.delete(rating)
                entry = db.scalar(select(BeerEntry).where(BeerEntry.id == beer['id']))
                if entry:
                    db.delete(entry)
            db.commit()


@pytest.mark.usefixtures('database')
class TestAdminBeers:
    async def test_list_all_beers(
        self,
        async_client: AsyncClient,
        admin_token: str,
        admin_list_beers: list[dict],
    ) -> None:
        response = await async_client.get('/admin/beers', headers={'Authorization': f'Bearer {admin_token}'})
        assert response.status_code == 200
        beers = [AdminBeerEntryOut.model_validate(beer) for beer in response.json()]
        beers_by_id = {beer.id: beer for beer in beers}

        for seeded_beer in admin_list_beers:
            assert seeded_beer['id'] in beers_by_id

        seeded_names = {beers_by_id[seeded_beer['id']].beer_name for seeded_beer in admin_list_beers}
        assert seeded_names == {_ALICE_BEER_PAYLOAD['beer_name'], _BOB_BEER_PAYLOAD['beer_name']}

        seeded_display_names = {beers_by_id[seeded_beer['id']].display_name for seeded_beer in admin_list_beers}
        assert seeded_display_names == {'Alice', 'Bob'}

    async def test_all_beers_returns_error_missing_token(self, async_client: AsyncClient) -> None:
        response = await async_client.get('/admin/beers')
        assert response.status_code == 401
