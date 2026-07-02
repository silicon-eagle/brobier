from collections.abc import Callable, Generator
from datetime import timedelta

import pytest
from brobier.core.security import encrypt_field
from brobier.core.time import current_time
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, CalendarEntry, User
from brobier.schemas.admin import AdminCalendarBeerOut, AdminCalendarEntryOut, CalendarBeerAssign
from brobier.schemas.calendar import CalendarEntryOut
from brobier.seeds.seed import _get_seed_years
from brobier.services.calendar_service import (
    assign_beer,
    create_calendar_year,
    delete_calendar_year,
    get_calendar_day,
    list_admin_calendar,
    list_calendar,
    list_years,
    unassign_beer,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def make_beer_entry(database: None, tst_globals: dict[str, str]) -> Generator[Callable[..., int]]:  # noqa: ARG001
    created_ids: list[int] = []

    def create(*, user_email: str | None = None, year: int | None = None) -> int:
        email = user_email or tst_globals['USER']
        with Session(get_app_engine()) as db:
            user = db.scalar(select(User).filter_by(email=email))
            assert user is not None
            created_beer = BeerEntry(
                user_id=user.id,
                year=year or current_time().year,
                beer_name_encrypted=encrypt_field('Test Beer'),
                brewery_encrypted=encrypt_field('Test Brewery'),
                untappd_url_encrypted=encrypt_field('https://untappd.example/test-beer'),
                comment_encrypted=encrypt_field('Tastes great'),
                bought_from='Test Shop',
                bought_at=current_time(),
            )
            db.add(created_beer)
            db.commit()
            db.refresh(created_beer)
            created_ids.append(created_beer.id)
            return created_beer.id

    yield create

    with Session(get_app_engine()) as db:
        # Unlink from any calendar entries first (including seeded ones)
        linked = db.scalars(select(CalendarEntry).where(CalendarEntry.beer_entry_id.in_(created_ids))).all()
        for entry in linked:
            entry.beer_entry_id = None
        db.commit()
        for beer_id in created_ids:
            beer = db.scalar(select(BeerEntry).filter_by(id=beer_id))
            if beer:
                db.delete(beer)
        db.commit()


@pytest.fixture
def make_calendar_entry(database: None) -> Generator[Callable[..., int]]:  # noqa: ARG001
    created_ids: list[int] = []

    def create(
        *,
        year: int,
        day: int,
        unlock_offset_days: int,
        title: str,
        content: str = '',
        image_url: str | None = None,
        beer_entry_id: int | None = None,
    ) -> int:
        with Session(get_app_engine()) as db:
            entry = CalendarEntry(
                year=year,
                day=day,
                unlock_date=current_time() + timedelta(days=unlock_offset_days),
                title=title,
                content=content,
                image_url=image_url,
                beer_entry_id=beer_entry_id,
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            created_ids.append(entry.id)
            return entry.id

    yield create

    with Session(get_app_engine()) as db:
        for entry_id in created_ids:
            entry = db.scalar(select(CalendarEntry).filter_by(id=entry_id))
            if entry:
                db.delete(entry)
        db.commit()


@pytest.mark.usefixtures('database')
class TestCalendarService:
    def test_list_years_returns_sorted_distinct_years(self) -> None:
        years = list_years()
        assert len(years) > 0

    def test_list_calendar_returns_current_year_by_default(self) -> None:
        seeded_year = list_years()[0].year

        entries = list_calendar(year=seeded_year)

        assert len(entries) >= 24
        assert all(entry.year == seeded_year for entry in entries)
        assert [entry.day for entry in entries] == list(range(1, 25))

    def test_list_calendar_does_not_show_beers_if_locked(self, make_beer_entry: Callable[..., int]) -> None:
        year = _get_seed_years()[-1]
        beer_id = make_beer_entry(year=year)
        assign_beer(year, 1, CalendarBeerAssign(beer_entry_id=beer_id))
        calendar = list_calendar(year)
        assert calendar[0].beer is None

    def test_list_calendar_returns_entries_for_requested_year(self, make_calendar_entry: Callable[..., int]) -> None:
        year = current_time().year + 3
        make_calendar_entry(year=year, day=2, unlock_offset_days=1, title='Locked entry')
        make_calendar_entry(year=year, day=1, unlock_offset_days=-1, title='Unlocked entry', content='Visible now')

        entries = list_calendar(year)

        assert [entry.day for entry in entries] == [1, 2]
        assert isinstance(entries[0], CalendarEntryOut)
        assert entries[0].content == 'Visible now'
        assert isinstance(entries[1], CalendarEntryOut)

    def test_get_calendar_day_returns_unlocked_entry_with_beer(
        self,
        make_beer_entry: Callable[..., int],
        make_calendar_entry: Callable[..., int],
    ) -> None:
        year = current_time().year + 4
        beer_entry_id = make_beer_entry()
        make_calendar_entry(
            year=year,
            day=5,
            unlock_offset_days=-1,
            title='Beer day',
            content='Beer reveal',
            image_url='https://example.com/beer.png',
            beer_entry_id=beer_entry_id,
        )

        entry = get_calendar_day(day=5, year=year)

        assert entry.is_locked is False
        assert entry.title == 'Beer day'
        assert entry.content == 'Beer reveal'
        assert entry.image_url == 'https://example.com/beer.png'
        assert entry.beer is not None
        assert entry.beer.beer_name == 'Test Beer'
        assert entry.beer.brewery == 'Test Brewery'
        assert entry.beer.untappd_url == 'https://untappd.example/test-beer'
        assert entry.beer.comment == 'Tastes great'
        assert entry.beer.bought_from == 'Test Shop'
        assert entry.beer.submitted_by == 'Alice'
        assert entry.beer.ratings == []

    def test_get_calendar_day_raises_for_locked_and_missing_entries(self, make_calendar_entry: Callable[..., int]) -> None:
        year = current_time().year + 5
        make_calendar_entry(year=year, day=6, unlock_offset_days=1, title='Still locked')

        with pytest.raises(PermissionError, match=r'This day is not yet unlocked\.'):
            get_calendar_day(day=6, year=year)

        with pytest.raises(ValueError, match=r'Calendar day not found\.'):
            get_calendar_day(day=24, year=year)


@pytest.mark.usefixtures('database')
class TestAdminCalendarService:
    def test_list_admin_calendar_returns_seeded_entries(self) -> None:
        year = _get_seed_years()[0]

        entries = list_admin_calendar(year)

        assert len(entries) == 24
        assert all(isinstance(e, AdminCalendarEntryOut) for e in entries)
        assert [e.day for e in entries] == list(range(1, 25))

    def test_create_calendar_year_inserts_all_missing_days(self, make_calendar_entry: Callable[..., int]) -> None:
        year = current_time().year + 10
        make_calendar_entry(year=year, day=3, unlock_offset_days=1, title='Existing entry')

        create_calendar_year(year)

        entries = list_admin_calendar(year)
        assert len(entries) == 24
        assert [entry.day for entry in entries] == list(range(1, 25))
        assert entries[2].title == 'Existing entry'

    def test_delete_calendar_year_removes_all_days(self) -> None:
        year = current_time().year + 11
        create_calendar_year(year)

        delete_calendar_year(year)

        assert list_admin_calendar(year) == []

    def test_delete_calendar_year_raises_if_any_day_has_assigned_beer(self, make_beer_entry: Callable[..., int]) -> None:
        year = current_time().year + 12
        create_calendar_year(year)
        beer_id = make_beer_entry(year=year)
        assign_beer(year, 7, CalendarBeerAssign(beer_entry_id=beer_id))

        with pytest.raises(ValueError, match=r'assigned beer'):
            delete_calendar_year(year)

        entries = list_admin_calendar(year)
        assert len(entries) == 24
        assert entries[6].beer_entry_id == beer_id

    def test_assign_beer_links_beer_to_calendar_day(self, make_beer_entry: Callable[..., int]) -> None:
        year = _get_seed_years()[0]
        beer_id = make_beer_entry(year=year)

        entry = assign_beer(year, 1, CalendarBeerAssign(beer_entry_id=beer_id))

        assert isinstance(entry, AdminCalendarEntryOut)
        assert entry.beer_entry_id == beer_id
        assert entry.beer is not None
        assert entry.beer.id == beer_id

    def test_list_admin_calendar_returns_beer_entries_if_locked(self, make_beer_entry: Callable[..., int]) -> None:
        year = _get_seed_years()[-1]
        beer_id = make_beer_entry(year=year)

        assign_beer(year, 1, CalendarBeerAssign(beer_entry_id=beer_id))
        calendar = list_admin_calendar(year)
        assert calendar[0].beer_entry_id == beer_id
        assert calendar[0].beer is not None
        assert isinstance(calendar[0].beer, AdminCalendarBeerOut)

    def test_assign_beer_raises_for_unknown_calendar_day(self, make_beer_entry: Callable[..., int]) -> None:
        beer_id = make_beer_entry()

        with pytest.raises(ValueError, match=r'Calendar entry not found\.'):
            assign_beer(9999, 1, CalendarBeerAssign(beer_entry_id=beer_id))

    def test_assign_beer_raises_for_unknown_beer(self) -> None:
        year = _get_seed_years()[0]

        with pytest.raises(ValueError, match=r'Beer entry not found\.'):
            assign_beer(year, 1, CalendarBeerAssign(beer_entry_id=999999))

    def test_assign_beer_raises_if_already_assigned_to_another_day(self, make_beer_entry: Callable[..., int]) -> None:
        year = _get_seed_years()[0]
        beer_id = make_beer_entry(year=year)
        assign_beer(year, 2, CalendarBeerAssign(beer_entry_id=beer_id))

        with pytest.raises(ValueError, match=r'already assigned'):
            assign_beer(year, 3, CalendarBeerAssign(beer_entry_id=beer_id))

    def test_assign_beer_raises_if_beer_is_from_different_year(self, make_beer_entry: Callable[..., int]) -> None:
        year = _get_seed_years()[0]
        beer_id = make_beer_entry(year=year + 1)

        with pytest.raises(ValueError, match=r'different calendar year'):
            assign_beer(year, 3, CalendarBeerAssign(beer_entry_id=beer_id))

    def test_unassign_beer_removes_beer_from_calendar_day(self, make_beer_entry: Callable[..., int]) -> None:
        year = _get_seed_years()[0]
        beer_id = make_beer_entry(year=year)
        assign_beer(year, 4, CalendarBeerAssign(beer_entry_id=beer_id))

        entry = unassign_beer(year, 4)

        assert entry.beer_entry_id is None
        assert entry.beer is None

    def test_unassign_beer_raises_for_unknown_calendar_day(self) -> None:
        with pytest.raises(ValueError, match=r'Calendar entry not found\.'):
            unassign_beer(9999, 1)
