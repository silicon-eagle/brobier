from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from brobier.core.security import decrypt_field
from brobier.db.engine import get_admin_engine
from brobier.db.models import BeerEntry, CalendarEntry
from brobier.schemas.admin import (
    AdminCalendarBeerOut,
    AdminCalendarEntryOut,
    CalendarBeerAssign,
    CalendarEntryCreate,
    CalendarEntryUpdate,
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
        id=entry.id,
        year=entry.year,
        day=entry.day,
        unlock_date=entry.unlock_date,
        title=entry.title,
        content=entry.content,
        image_url=entry.image_url,
        beer_entry_id=entry.beer_entry_id,
        beer=beer_out,
    )


@router.get('', response_model=list[AdminCalendarEntryOut])
def list_calendar(year: int | None = None) -> list[AdminCalendarEntryOut]:
    with Session(get_admin_engine()) as db:
        query = select(CalendarEntry).order_by(CalendarEntry.year, CalendarEntry.day)
        if year is not None:
            query = query.where(CalendarEntry.year == year)
        entries = db.scalars(query).all()
        return [_parse_admin_entry(entry) for entry in entries]


@router.post('', response_model=AdminCalendarEntryOut, status_code=status.HTTP_201_CREATED)
def create_calendar_entry(body: CalendarEntryCreate) -> AdminCalendarEntryOut:
    with Session(get_admin_engine()) as db:
        entry = CalendarEntry(
            year=body.year,
            day=body.day,
            unlock_date=body.unlock_date,
            title=body.title,
            content=body.content,
            image_url=body.image_url,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return _parse_admin_entry(entry)


@router.put('/{entry_id}', response_model=AdminCalendarEntryOut)
def update_calendar_entry(entry_id: int, body: CalendarEntryUpdate) -> AdminCalendarEntryOut:
    with Session(get_admin_engine()) as db:
        entry = db.scalar(select(CalendarEntry).where(CalendarEntry.id == entry_id))
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Calendar entry not found.')

        if body.unlock_date is not None:
            entry.unlock_date = body.unlock_date
        if body.title is not None:
            entry.title = body.title
        if body.content is not None:
            entry.content = body.content
        if body.image_url is not None:
            entry.image_url = body.image_url

        db.commit()
        db.refresh(entry)
        return _parse_admin_entry(entry)


@router.delete('/{entry_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_calendar_entry(entry_id: int) -> None:
    with Session(get_admin_engine()) as db:
        entry = db.scalar(select(CalendarEntry).where(CalendarEntry.id == entry_id))
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Calendar entry not found.')
        db.delete(entry)
        db.commit()


@router.put('/{entry_id}/beer', response_model=AdminCalendarEntryOut)
def assign_beer(entry_id: int, body: CalendarBeerAssign) -> AdminCalendarEntryOut:
    with Session(get_admin_engine()) as db:
        entry = db.scalar(select(CalendarEntry).where(CalendarEntry.id == entry_id))
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Calendar entry not found.')
        beer = db.scalar(select(BeerEntry).where(BeerEntry.id == body.beer_entry_id))
        if not beer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Beer entry not found.')

        entry.beer_entry_id = body.beer_entry_id
        db.commit()
        db.refresh(entry)
        return _parse_admin_entry(entry)


@router.delete('/{entry_id}/beer', response_model=AdminCalendarEntryOut)
def unassign_beer(entry_id: int) -> AdminCalendarEntryOut:
    with Session(get_admin_engine()) as db:
        entry = db.scalar(select(CalendarEntry).where(CalendarEntry.id == entry_id))
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Calendar entry not found.')

        entry.beer_entry_id = None
        db.commit()
        db.refresh(entry)
        return _parse_admin_entry(entry)
