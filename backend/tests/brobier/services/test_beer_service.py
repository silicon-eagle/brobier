from collections.abc import Generator

import pytest
from brobier.core.security import decrypt_field
from brobier.core.time import current_time
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, CalendarEntry, User
from brobier.schemas.beer import BeerEntryCreate, BeerEntryOut, BeerEntryUpdate
from brobier.schemas.user_rating import UserRatingCreate, UserRatingOut, UserRatingUpdate
from brobier.services.beers_service import (
    create_beer,
    create_rating,
    delete_beer,
    delete_rating,
    get_beers_for_user,
    update_beer,
    update_rating,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

_BEER_CREATE = BeerEntryCreate(
    year=current_time().year,
    beer_name='Test Lager',
    brewery='Test Brewery',
    untappd_url='https://untappd.com/test-beer',
    bought_from='Test Shop',
    bought_at=current_time(),
)


def _get_user(email: str) -> User:
    with Session(get_app_engine()) as db:
        user = db.scalar(select(User).filter_by(email=email))
        assert user is not None
        return user


@pytest.fixture
def beer(database: None, tst_globals: dict[str, str]) -> Generator[BeerEntryOut]:  # noqa: ARG001
    user = _get_user(tst_globals['USER'])
    created = create_beer(user.id, _BEER_CREATE)
    yield created
    try:
        delete_rating(created.id, user.id)
    except ValueError:
        pass
    try:
        delete_beer(created.id, user.id)
    except ValueError:
        pass


@pytest.mark.usefixtures('database')
class TestBeerService:
    def test_create_beer_returns_beer_out(self, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])

        created = create_beer(user.id, _BEER_CREATE)

        try:
            assert isinstance(created, BeerEntryOut)
            assert created.year == current_time().year
            assert created.beer_name == 'Test Lager'
            assert created.brewery == 'Test Brewery'
            assert created.bought_from == 'Test Shop'
            assert created.user_id == user.id
        finally:
            delete_beer(created.id, user.id)

    def test_encrypted_fields_are_not_stored_as_plaintext(self, beer: BeerEntryOut) -> None:
        with Session(get_app_engine()) as db:
            row: BeerEntry | None = db.scalar(select(BeerEntry).filter_by(id=beer.id))
            assert row is not None

        assert row.beer_name_encrypted != 'Test Lager'
        assert row.brewery_encrypted != 'Test Brewery'
        assert row.untappd_url_encrypted != 'https://untappd.com/test-beer'

        assert decrypt_field(row.beer_name_encrypted) == 'Test Lager'
        assert decrypt_field(row.brewery_encrypted) == 'Test Brewery'
        assert row.untappd_url_encrypted is not None
        assert decrypt_field(row.untappd_url_encrypted) == 'https://untappd.com/test-beer'

    @pytest.mark.usefixtures('beer')
    def test_get_beers_for_user_returns_own_beers(self, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])

        beers = get_beers_for_user(user.id)

        assert len(beers) >= 1
        assert all(b.user_id == user.id for b in beers)

    def test_update_beer_changes_fields(self, beer: BeerEntryOut, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])

        updated = update_beer(beer.id, user.id, BeerEntryUpdate(beer_name='Updated Lager', year=2025))

        assert updated.beer_name == 'Updated Lager'
        assert updated.year == 2025

    def test_update_beer_raises_for_wrong_user(self, beer: BeerEntryOut) -> None:
        bob = _get_user('bob@brobier.local')

        with pytest.raises(ValueError, match=r'Beer not found\.'):
            update_beer(beer.id, bob.id, BeerEntryUpdate(beer_name='Hacked'))

    def test_delete_beer_removes_it(self, beer: BeerEntryOut, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])
        before = len(get_beers_for_user(user.id))

        delete_beer(beer.id, user.id)

        assert len(get_beers_for_user(user.id)) == before - 1

    def test_delete_beer_raises_for_wrong_user(self, beer: BeerEntryOut) -> None:
        bob = _get_user('bob@brobier.local')

        with pytest.raises(ValueError, match=r'Beer not found\.'):
            delete_beer(beer.id, bob.id)

    def test_delete_beer_raises_if_assigned_to_calendar_day(self, beer: BeerEntryOut, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])

        with Session(get_app_engine()) as db:
            calendar_entry = CalendarEntry(
                year=current_time().year + 50,
                day=1,
                unlock_date=current_time(),
                title='Assigned beer',
                content='Assigned beer content',
                beer_entry_id=beer.id,
            )
            db.add(calendar_entry)
            db.commit()

            try:
                with pytest.raises(ValueError, match=r'Cannot delete beer assigned to a calendar day\.'):
                    delete_beer(beer.id, user.id)

                assert db.scalar(select(BeerEntry).filter_by(id=beer.id)) is not None
            finally:
                db.delete(calendar_entry)
                db.commit()

    def test_create_rating_returns_rating_out(self, beer: BeerEntryOut, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])

        rating = create_rating(beer.id, user.id, UserRatingCreate(rating=4.0, comment='Crisp'))

        assert isinstance(rating, UserRatingOut)
        assert rating.beer_entry_id == beer.id
        assert rating.rating == 4.0
        assert rating.comment == 'Crisp'

    def test_create_rating_raises_on_duplicate(self, beer: BeerEntryOut, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])
        create_rating(beer.id, user.id, UserRatingCreate(rating=3.0))

        with pytest.raises(ValueError, match=r'Rating already exists\.'):
            create_rating(beer.id, user.id, UserRatingCreate(rating=5.0))

    def test_create_rating_raises_for_missing_beer(self, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])

        with pytest.raises(ValueError, match=r'Beer not found\.'):
            create_rating(999999, user.id, UserRatingCreate(rating=3.0))

    def test_update_rating_changes_fields(self, beer: BeerEntryOut, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])
        create_rating(beer.id, user.id, UserRatingCreate(rating=3.0))

        updated = update_rating(beer.id, user.id, UserRatingUpdate(rating=5.0, comment='Actually great'))

        assert updated.rating == 5.0
        assert updated.comment == 'Actually great'

    def test_delete_rating_removes_it(self, beer: BeerEntryOut, tst_globals: dict[str, str]) -> None:
        user = _get_user(tst_globals['USER'])
        create_rating(beer.id, user.id, UserRatingCreate(rating=2.0))

        delete_rating(beer.id, user.id)

        with pytest.raises(ValueError, match=r'Rating not found\.'):
            delete_rating(beer.id, user.id)
