from fastapi import APIRouter, status

from brobier.schemas.admin import AdminCalendarEntryOut, CalendarBeerAssign
from brobier.services import calendar_service

router = APIRouter(tags=['admin:calendar'])


@router.get('', response_model=list[AdminCalendarEntryOut])
def list_calendar(year: int | None = None) -> list[AdminCalendarEntryOut]:
    return calendar_service.list_admin_calendar(year)


@router.put('/{year}', status_code=status.HTTP_204_NO_CONTENT)
def create_calendar_year(year: int) -> None:
    calendar_service.create_calendar_year(year)


@router.delete('/{year}', status_code=status.HTTP_204_NO_CONTENT)
def delete_calendar_year(year: int) -> None:
    calendar_service.delete_calendar_year(year)


@router.put('/{year}/{day}/beer', response_model=AdminCalendarEntryOut)
def assign_beer(year: int, day: int, body: CalendarBeerAssign) -> AdminCalendarEntryOut:
    return calendar_service.assign_beer(year, day, body)


@router.delete('/{year}/{day}/beer', response_model=AdminCalendarEntryOut)
def unassign_beer(year: int, day: int) -> AdminCalendarEntryOut:
    return calendar_service.unassign_beer(year, day)
