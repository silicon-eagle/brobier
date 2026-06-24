from datetime import timedelta

import pytest
from brobier.core.security import encrypt_field
from brobier.core.time import current_time
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, CalendarEntry, User
from brobier.schemas.calendar import CalendarEntryOut
from brobier.services.calendar_service import get_calendar_day, list_calendar, list_years
from sqlalchemy import select
from sqlalchemy.orm import Session


def _create_calendar_entry(
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
        return entry.id


def _create_beer_entry(*, user_email: str) -> int:
    with Session(get_app_engine()) as db:
        user = db.scalar(select(User).filter_by(email=user_email))
        assert user is not None

        beer = BeerEntry(
            user_id=user.id,
            year=current_time().year,
            beer_name_encrypted=encrypt_field('Test Beer'),
            brewery_encrypted=encrypt_field('Test Brewery'),
            untappd_url_encrypted=encrypt_field('https://untappd.example/test-beer'),
            comment_encrypted=encrypt_field('Tastes great'),
            bought_from='Test Shop',
            bought_at=current_time(),
        )
        db.add(beer)
        db.commit()
        db.refresh(beer)
        return beer.id


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

    def test_list_calendar_returns_entries_for_requested_year(self) -> None:
        year = current_time().year + 3
        _create_calendar_entry(year=year, day=2, unlock_offset_days=1, title='Locked entry')
        _create_calendar_entry(year=year, day=1, unlock_offset_days=-1, title='Unlocked entry', content='Visible now')

        entries = list_calendar(year)

        assert [entry.day for entry in entries] == [1, 2]
        assert isinstance(entries[0], CalendarEntryOut)
        assert entries[0].content == 'Visible now'
        assert isinstance(entries[1], CalendarEntryOut)

    def test_get_calendar_day_returns_unlocked_entry_with_beer(self, tst_globals: dict[str, str]) -> None:
        year = current_time().year + 4
        beer_entry_id = _create_beer_entry(user_email=tst_globals['USER'])
        _create_calendar_entry(
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

    def test_get_calendar_day_raises_for_locked_and_missing_entries(self) -> None:
        year = current_time().year + 5
        _create_calendar_entry(year=year, day=6, unlock_offset_days=1, title='Still locked')

        with pytest.raises(PermissionError, match=r'This day is not yet unlocked\.'):
            get_calendar_day(day=6, year=year)

        with pytest.raises(ValueError, match=r'Calendar day not found\.'):
            get_calendar_day(day=24, year=year)
