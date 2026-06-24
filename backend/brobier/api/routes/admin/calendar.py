from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from brobier.core.security import decrypt_field
from brobier.core.time import current_time
from brobier.db.engine import get_admin_engine
from brobier.db.models import BeerEntry, CalendarEntry
from brobier.schemas.admin import (
    AdminCalendarBeerOut,
    AdminCalendarEntryOut,
    CalendarBeerAssign,
)
from brobier.schemas.user_rating import UserRatingOut

router = APIRouter(tags=['admin:calendar'])


def _parse_admin_beer(beer: BeerEntry) -> AdminCalendarBeerOut:
    ratings = [UserRatingOut.model_validate(r) for r in beer.user_ratings]
    return AdminCalendarBeerOut(
        id=beer.id,
        user_id=beer.user_id,
        display_name=beer.user.display_name,
        beer_name=decrypt_field(beer.beer_name_encrypted),
        brewery=decrypt_field(beer.brewery_encrypted),
        untappd_url=decrypt_field(beer.untappd_url_encrypted) if beer.untappd_url_encrypted else None,
        comment=decrypt_field(beer.comment_encrypted) if beer.comment_encrypted else None,
        bought_from=beer.bought_from,
        bought_at=beer.bought_at,
        ratings=ratings,
    )


def _parse_admin_entry(entry: CalendarEntry) -> AdminCalendarEntryOut:
    beer_out = _parse_admin_beer(entry.beer_entry) if entry.beer_entry else None
    return AdminCalendarEntryOut(
        year=entry.year,
        day=entry.day,
        unlock_date=entry.unlock_date,
        title=entry.title,
        content=entry.content,
        image_url=entry.image_url,
        beer_entry_id=entry.beer_entry_id,
        beer=beer_out,
    )


def _get_calendar_entry(db: Session, year: int, day: int) -> CalendarEntry:
    entry = db.scalar(select(CalendarEntry).filter_by(year=year, day=day))
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Calendar entry not found.')
    return entry


@router.get('', response_model=list[AdminCalendarEntryOut])
def list_calendar(year: int | None = None) -> list[AdminCalendarEntryOut]:
    effective_year = year or current_time().year
    with Session(get_admin_engine()) as db:
        entries = db.scalars(select(CalendarEntry).filter_by(year=effective_year).order_by(CalendarEntry.day)).all()
        return [_parse_admin_entry(entry) for entry in entries]


@router.put('/{year}/{day}/beer', response_model=AdminCalendarEntryOut)
def assign_beer(year: int, day: int, body: CalendarBeerAssign) -> AdminCalendarEntryOut:
    with Session(get_admin_engine()) as db:
        entry = _get_calendar_entry(db, year, day)
        beer = db.scalar(select(BeerEntry).filter_by(id=body.beer_entry_id))
        if not beer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Beer entry not found.')
        if beer.calendar_entry and (beer.calendar_entry.year != year or beer.calendar_entry.day != day):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Beer entry is already assigned to a calendar day.')

        entry.beer_entry_id = body.beer_entry_id
        db.commit()
        db.refresh(entry)
        return _parse_admin_entry(entry)


@router.delete('/{year}/{day}/beer', response_model=AdminCalendarEntryOut)
def unassign_beer(year: int, day: int) -> AdminCalendarEntryOut:
    with Session(get_admin_engine()) as db:
        entry = _get_calendar_entry(db, year, day)

        entry.beer_entry_id = None
        db.commit()
        db.refresh(entry)
        return _parse_admin_entry(entry)
