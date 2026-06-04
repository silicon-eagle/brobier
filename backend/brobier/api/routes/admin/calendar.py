from fastapi import APIRouter, HTTPException, status

from brobier.schemas.admin import (
    AdminCalendarEntryOut,
    CalendarBeerAssign,
    CalendarEntryCreate,
    CalendarEntryUpdate,
)

router = APIRouter(tags=['admin:calendar'])


@router.get('', response_model=list[AdminCalendarEntryOut])
def list_calendar(year: int | None = None) -> list[AdminCalendarEntryOut]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.post('', response_model=AdminCalendarEntryOut, status_code=status.HTTP_201_CREATED)
def create_calendar_entry(body: CalendarEntryCreate) -> AdminCalendarEntryOut:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.put('/{entry_id}', response_model=AdminCalendarEntryOut)
def update_calendar_entry(entry_id: int, body: CalendarEntryUpdate) -> AdminCalendarEntryOut:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.delete('/{entry_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_calendar_entry(entry_id: int) -> None:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.put('/{entry_id}/beer', response_model=AdminCalendarEntryOut)
def assign_beer(entry_id: int, body: CalendarBeerAssign) -> AdminCalendarEntryOut:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.delete('/{entry_id}/beer', response_model=AdminCalendarEntryOut)
def unassign_beer(entry_id: int) -> AdminCalendarEntryOut:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')
