from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from brobier.core.security import decrypt_field
from brobier.core.time import current_time
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, CalendarEntry
from brobier.schemas.calendar import CalendarBeerOut, CalendarEntryOut, YearOut
from brobier.schemas.user_rating import UserRatingOut


def _make_beer_out(beer_entry: BeerEntry) -> CalendarBeerOut:
    ratings = [UserRatingOut.model_validate(r) for r in beer_entry.user_ratings]
    return CalendarBeerOut(
        id=beer_entry.id,
        beer_name=decrypt_field(beer_entry.beer_name_encrypted),
        brewery=decrypt_field(beer_entry.brewery_encrypted),
        untappd_url=decrypt_field(beer_entry.untappd_url_encrypted) if beer_entry.untappd_url_encrypted else None,
        comment=decrypt_field(beer_entry.comment_encrypted) if beer_entry.comment_encrypted else None,
        bought_from=beer_entry.bought_from,
        submitted_by=beer_entry.user.display_name,
        ratings=ratings,
    )


def _make_entry_out(entry: CalendarEntry, now: datetime) -> CalendarEntryOut:
    if entry.unlock_date > now:
        # Only return the ID and unlock date for locked entries
        return CalendarEntryOut(
            id=entry.id,
            year=entry.year,
            day=entry.day,
            unlock_date=entry.unlock_date,
            title=None,
            content=None,
            image_url=None,
            is_locked=True,
        )
    else:
        # Only retrieve the beer entry if it's unlocked
        beer_out = _make_beer_out(entry.beer_entry) if entry.beer_entry else None
        if beer_out is None:
            logger.warning(f'Calendar entry {entry.id} {entry.title} is unlocked but has no beer entry!')
        return CalendarEntryOut(
            id=entry.id,
            year=entry.year,
            day=entry.day,
            unlock_date=entry.unlock_date,
            title=entry.title,
            content=entry.content,
            image_url=entry.image_url,
            is_locked=False,
            beer=beer_out,
        )


def list_years() -> list[YearOut]:
    with Session(get_app_engine()) as db:
        years = db.scalars(select(CalendarEntry.year).distinct().order_by(CalendarEntry.year)).all()
        return [YearOut(year=y) for y in years]


def list_calendar(year: int | None = None) -> list[CalendarEntryOut]:
    effective_year = year or current_time().year
    now = current_time()
    with Session(get_app_engine()) as db:
        entries = db.scalars(select(CalendarEntry).filter_by(year=effective_year).order_by(CalendarEntry.day)).all()
        return [_make_entry_out(entry, now) for entry in entries]


def get_calendar_day(day: int, year: int) -> CalendarEntryOut:
    now = current_time()
    with Session(get_app_engine()) as db:
        entry = db.scalar(select(CalendarEntry).filter_by(year=year, day=day))
        if not entry:
            raise ValueError('Calendar day not found.')
        if entry.unlock_date > now:
            raise PermissionError('This day is not yet unlocked.')
        entry_out = _make_entry_out(entry, now)
        return entry_out
