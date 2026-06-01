from fastapi import APIRouter, HTTPException, status

from backend.schemas.calendar import CalendarEntryLockedOut, CalendarEntryUnlockedOut, YearOut

router = APIRouter(tags=['calendar'])

CalendarEntryOut = CalendarEntryLockedOut | CalendarEntryUnlockedOut


@router.get('/years', response_model=list[YearOut])
def list_years() -> list[YearOut]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.get('', response_model=list[CalendarEntryOut])
def list_calendar(year: int | None = None) -> list[CalendarEntryOut]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')


@router.get('/{day}', response_model=CalendarEntryUnlockedOut)
def get_calendar_day(day: int, year: int) -> CalendarEntryUnlockedOut:
    # year is required — FastAPI returns 422 automatically if omitted.
    # Returns 403 if unlock_date > now (implemented in service layer).
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')
