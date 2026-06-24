from fastapi import APIRouter, HTTPException, status

from brobier.schemas.calendar import CalendarEntryOut, YearOut
from brobier.services import calendar_service

router = APIRouter(tags=['calendar'])


@router.get('/years', response_model=list[YearOut])
def list_years() -> list[YearOut]:
    return calendar_service.list_years()


@router.get('', response_model=list[CalendarEntryOut])
def list_calendar(year: int | None = None) -> list[CalendarEntryOut]:
    return calendar_service.list_calendar(year)


@router.get('/{year}/{day}', response_model=CalendarEntryOut)
def get_calendar_day(day: int, year: int) -> CalendarEntryOut:
    # year is required — FastAPI returns 422 automatically if omitted.
    # Returns 403 if unlock_date > now (implemented in calendar_service).
    try:
        return calendar_service.get_calendar_day(day, year)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
