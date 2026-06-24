from fastapi import APIRouter, HTTPException, status

from brobier.schemas.admin import AdminCalendarEntryOut, CalendarBeerAssign
from brobier.services import calendar_service

router = APIRouter(tags=['admin:calendar'])


@router.get('', response_model=list[AdminCalendarEntryOut])
def list_calendar(year: int | None = None) -> list[AdminCalendarEntryOut]:
    return calendar_service.list_admin_calendar(year)


@router.put('/{year}/{day}/beer', response_model=AdminCalendarEntryOut)
def assign_beer(year: int, day: int, body: CalendarBeerAssign) -> AdminCalendarEntryOut:
    try:
        return calendar_service.assign_beer(year, day, body)
    except ValueError as e:
        if 'already assigned' in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete('/{year}/{day}/beer', response_model=AdminCalendarEntryOut)
def unassign_beer(year: int, day: int) -> AdminCalendarEntryOut:
    try:
        return calendar_service.unassign_beer(year, day)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
