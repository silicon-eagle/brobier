from datetime import datetime

from pydantic import BaseModel

from brobier.schemas.user_rating import UserRatingOut


class CalendarBeerOut(BaseModel):
    id: int
    beer_name: str
    brewery: str
    untappd_url: str | None
    comment: str | None
    bought_from: str
    submitted_by: str
    ratings: list[UserRatingOut] = []

    model_config = {'from_attributes': True}


class CalendarEntryLockedOut(BaseModel):
    id: int
    year: int
    day: int
    unlock_date: datetime
    title: str
    is_locked: bool = True

    model_config = {'from_attributes': True}


class CalendarEntryUnlockedOut(BaseModel):
    id: int
    year: int
    day: int
    unlock_date: datetime
    title: str
    content: str
    image_url: str | None
    is_locked: bool = False
    beer: CalendarBeerOut | None = None

    model_config = {'from_attributes': True}


class YearOut(BaseModel):
    year: int
