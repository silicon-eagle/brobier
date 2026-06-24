from collections.abc import AsyncGenerator

import pytest
from brobier.auth.jwt import create_access_token
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, User, UserRating
from brobier.schemas.beer import BeerEntryOut
from brobier.schemas.user_rating import UserRatingOut
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

_BEER_PAYLOAD = {
    'year': 2024,
    'beer_name': 'Test Lager',
    'brewery': 'Test Brewery',
    'bought_from': 'Test Shop',
    'bought_at': '2024-12-01T12:00:00Z',
}

_RATING_PAYLOAD = {
    'rating': 4.0,
    'comment': 'Smooth and crisp',
}


@pytest.fixture
def alice_token() -> str:
    with Session(get_app_engine()) as db:
        user = db.scalar(select(User).where(User.email == 'alice@brobier.local'))
        assert user is not None
    return create_access_token(user.id, user.role)


@pytest.fixture
def bob_token() -> str:
    with Session(get_app_engine()) as db:
        user = db.scalar(select(User).where(User.email == 'bob@brobier.local'))
        assert user is not None
    return create_access_token(user.id, user.role)


@pytest.fixture
async def alice_beer(async_client: AsyncClient, alice_token: str) -> AsyncGenerator[dict]:
    response = await async_client.post(
        '/beers',
        json=_BEER_PAYLOAD,
        headers={'Authorization': f'Bearer {alice_token}'},
    )
    assert response.status_code == 201
    beer = response.json()
    yield beer
    with Session(get_app_engine()) as db:
        # Delete any ratings first to avoid FK violations
        ratings = db.scalars(select(UserRating).where(UserRating.beer_entry_id == beer['id'])).all()
        for rating in ratings:
            db.delete(rating)
        entry = db.scalar(select(BeerEntry).where(BeerEntry.id == beer['id']))
        if entry:
            db.delete(entry)
        db.commit()


@pytest.fixture
async def alice_rating(async_client: AsyncClient, alice_token: str, alice_beer: dict) -> AsyncGenerator[dict]:
    response = await async_client.post(
        f'/beers/{alice_beer["id"]}/ratings',
        json=_RATING_PAYLOAD,
        headers={'Authorization': f'Bearer {alice_token}'},
    )
    assert response.status_code == 201
    rating = response.json()
    yield rating
    with Session(get_app_engine()) as db:
        entry = db.scalar(select(UserRating).where(UserRating.id == rating['id']))
        if entry:
            db.delete(entry)
            db.commit()


@pytest.mark.usefixtures('database')
class TestBeerRoutes:
    async def test_get_my_beers_includes_own_beer(self, async_client: AsyncClient, alice_token: str, alice_beer: dict) -> None:
        response = await async_client.get('/beers/me', headers={'Authorization': f'Bearer {alice_token}'})
        assert response.status_code == 200
        ids = [b['id'] for b in response.json()]
        assert alice_beer['id'] in ids

    async def test_get_my_beers_excludes_other_users_beers(self, async_client: AsyncClient, alice_token: str, bob_token: str) -> None:
        bob_response = await async_client.post('/beers', json=_BEER_PAYLOAD, headers={'Authorization': f'Bearer {bob_token}'})
        assert bob_response.status_code == 201
        bob_beer_id = bob_response.json()['id']
        try:
            response = await async_client.get('/beers/me', headers={'Authorization': f'Bearer {alice_token}'})
            assert response.status_code == 200
            ids = [b['id'] for b in response.json()]
            assert bob_beer_id not in ids
        finally:
            with Session(get_app_engine()) as db:
                entry = db.scalar(select(BeerEntry).where(BeerEntry.id == bob_beer_id))
                if entry:
                    db.delete(entry)
                    db.commit()

    async def test_get_my_beers_requires_auth(self, async_client: AsyncClient) -> None:
        response = await async_client.get('/beers/me')
        assert response.status_code == 401

    async def test_create_beer(self, async_client: AsyncClient, alice_token: str) -> None:
        response = await async_client.post('/beers', json=_BEER_PAYLOAD, headers={'Authorization': f'Bearer {alice_token}'})
        assert response.status_code == 201
        beer = BeerEntryOut.model_validate(response.json())
        assert beer.beer_name == _BEER_PAYLOAD['beer_name']
        assert beer.brewery == _BEER_PAYLOAD['brewery']
        assert beer.bought_from == _BEER_PAYLOAD['bought_from']
        assert beer.untappd_url is None
        assert beer.comment is None

        response = await async_client.get('/beers/me', headers={'Authorization': f'Bearer {alice_token}'})
        validated_response = [BeerEntryOut.model_validate(b) for b in response.json()]
        assert response.status_code == 200
        assert validated_response[0].beer_name == _BEER_PAYLOAD['beer_name']
        assert validated_response[0].brewery == _BEER_PAYLOAD['brewery']
        assert validated_response[0].bought_from == _BEER_PAYLOAD['bought_from']
        assert validated_response[0].untappd_url is None
        assert validated_response[0].comment is None

    async def test_create_beer_with_optional_fields(self, async_client: AsyncClient, alice_token: str) -> None:
        payload = {**_BEER_PAYLOAD, 'untappd_url': 'https://untappd.com/b/test', 'comment': 'A fine ale'}
        response = await async_client.post('/beers', json=payload, headers={'Authorization': f'Bearer {alice_token}'})
        assert response.status_code == 201
        beer = BeerEntryOut.model_validate(response.json())
        assert beer.untappd_url == 'https://untappd.com/b/test'
        assert beer.comment == 'A fine ale'

    async def test_create_beer_requires_auth(self, async_client: AsyncClient) -> None:
        response = await async_client.post('/beers', json=_BEER_PAYLOAD)
        assert response.status_code == 401

    async def test_update_beer(self, async_client: AsyncClient, alice_token: str, alice_beer: dict) -> None:
        response = await async_client.put(
            f'/beers/{alice_beer["id"]}',
            json={'beer_name': 'Updated Lager', 'brewery': 'Updated Brewery'},
            headers={'Authorization': f'Bearer {alice_token}'},
        )
        assert response.status_code == 200
        beer = BeerEntryOut.model_validate(response.json())
        assert beer.beer_name == 'Updated Lager'
        assert beer.brewery == 'Updated Brewery'
        assert beer.bought_from == _BEER_PAYLOAD['bought_from']  # unchanged

    async def test_update_beer_not_found(self, async_client: AsyncClient, alice_token: str) -> None:
        response = await async_client.put(
            '/beers/999999',
            json={'beer_name': 'Ghost Beer'},
            headers={'Authorization': f'Bearer {alice_token}'},
        )
        assert response.status_code == 404

    async def test_update_beer_other_user_returns_404(self, async_client: AsyncClient, bob_token: str, alice_beer: dict) -> None:
        response = await async_client.put(
            f'/beers/{alice_beer["id"]}',
            json={'beer_name': 'Stolen Beer'},
            headers={'Authorization': f'Bearer {bob_token}'},
        )
        assert response.status_code == 404

    async def test_delete_beer(self, async_client: AsyncClient, alice_token: str, alice_beer: dict) -> None:
        response = await async_client.delete(f'/beers/{alice_beer["id"]}', headers={'Authorization': f'Bearer {alice_token}'})
        assert response.status_code == 204
        get_response = await async_client.get('/beers/me', headers={'Authorization': f'Bearer {alice_token}'})
        ids = [b['id'] for b in get_response.json()]
        assert alice_beer['id'] not in ids

    async def test_delete_beer_not_found(self, async_client: AsyncClient, alice_token: str) -> None:
        response = await async_client.delete('/beers/999999', headers={'Authorization': f'Bearer {alice_token}'})
        assert response.status_code == 404

    async def test_delete_beer_other_user_returns_404(self, async_client: AsyncClient, bob_token: str, alice_beer: dict) -> None:
        response = await async_client.delete(f'/beers/{alice_beer["id"]}', headers={'Authorization': f'Bearer {bob_token}'})
        assert response.status_code == 404

    async def test_create_rating(self, async_client: AsyncClient, alice_token: str, alice_beer: dict) -> None:
        response = await async_client.post(
            f'/beers/{alice_beer["id"]}/ratings',
            json=_RATING_PAYLOAD,
            headers={'Authorization': f'Bearer {alice_token}'},
        )
        assert response.status_code == 201
        rating = UserRatingOut.model_validate(response.json())
        assert rating.rating == _RATING_PAYLOAD['rating']
        assert rating.comment == _RATING_PAYLOAD['comment']
        assert rating.beer_entry_id == alice_beer['id']

    @pytest.mark.usefixtures('alice_rating')
    async def test_create_rating_duplicate_returns_409(self, async_client: AsyncClient, alice_token: str, alice_beer: dict) -> None:
        response = await async_client.post(
            f'/beers/{alice_beer["id"]}/ratings',
            json=_RATING_PAYLOAD,
            headers={'Authorization': f'Bearer {alice_token}'},
        )
        assert response.status_code == 409

    async def test_create_rating_beer_not_found(self, async_client: AsyncClient, alice_token: str) -> None:
        response = await async_client.post(
            '/beers/999999/ratings',
            json=_RATING_PAYLOAD,
            headers={'Authorization': f'Bearer {alice_token}'},
        )
        assert response.status_code == 404

    @pytest.mark.usefixtures('alice_rating')
    async def test_update_rating(self, async_client: AsyncClient, alice_token: str, alice_beer: dict) -> None:
        response = await async_client.put(
            f'/beers/{alice_beer["id"]}/ratings/me',
            json={'rating': 3.5, 'comment': 'Actually just okay'},
            headers={'Authorization': f'Bearer {alice_token}'},
        )
        assert response.status_code == 200
        rating = UserRatingOut.model_validate(response.json())
        assert rating.rating == 3.5
        assert rating.comment == 'Actually just okay'

    async def test_update_rating_not_found(self, async_client: AsyncClient, alice_token: str, alice_beer: dict) -> None:
        response = await async_client.put(
            f'/beers/{alice_beer["id"]}/ratings/me',
            json={'rating': 3.0},
            headers={'Authorization': f'Bearer {alice_token}'},
        )
        assert response.status_code == 404

    @pytest.mark.usefixtures('alice_rating')
    async def test_delete_rating(self, async_client: AsyncClient, alice_token: str, alice_beer: dict) -> None:
        response = await async_client.delete(
            f'/beers/{alice_beer["id"]}/ratings/me',
            headers={'Authorization': f'Bearer {alice_token}'},
        )
        assert response.status_code == 204

    async def test_delete_rating_not_found(self, async_client: AsyncClient, alice_token: str, alice_beer: dict) -> None:
        response = await async_client.delete(
            f'/beers/{alice_beer["id"]}/ratings/me',
            headers={'Authorization': f'Bearer {alice_token}'},
        )
        assert response.status_code == 404
