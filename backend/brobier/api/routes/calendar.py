from fastapi import APIRouter, HTTPException, status

from brobier.schemas.calendar import CalendarEntryLockedOut, CalendarEntryUnlockedOut, YearOut
from brobier.services import calendar_service

router = APIRouter(tags=['calendar'])

CalendarEntryOut = CalendarEntryLockedOut | CalendarEntryUnlockedOut


@router.get('/years', response_model=list[YearOut])
def list_years() -> list[YearOut]:
    return calendar_service.list_years()


@router.get('', response_model=list[CalendarEntryOut])
def list_calendar(year: int | None = None) -> list[CalendarEntryOut]:
    return calendar_service.list_calendar(year)


@router.get('/{day}', response_model=CalendarEntryUnlockedOut)
def get_calendar_day(day: int, year: int) -> CalendarEntryUnlockedOut:
    # year is required — FastAPI returns 422 automatically if omitted.
    # Returns 403 if unlock_date > now (implemented in service layer).
    try:
        return calendar_service.get_calendar_day(day, year)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
