import uuid
from datetime import datetime

from pydantic import BaseModel

from brobier.db.models.user import UserRole
from brobier.schemas.user_rating import UserRatingOut

# ── Users ──────────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class UserCreate(BaseModel):
    email: str
    display_name: str
    role: UserRole = UserRole.user
    is_active: bool = True


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


# ── Beers ──────────────────────────────────────────────────────────────────────

class AdminBeerEntryOut(BaseModel):
    id: int
    user_id: uuid.UUID
    display_name: str  # owner display name
    beer_name: str
    brewery: str
    untappd_url: str | None
    comment: str | None
    bought_from: str
    bought_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


# ── Calendar ───────────────────────────────────────────────────────────────────

class AdminCalendarBeerOut(BaseModel):
    id: int
    user_id: uuid.UUID
    display_name: str
    beer_name: str
    brewery: str
    untappd_url: str | None
    comment: str | None
    bought_from: str
    bought_at: datetime
    ratings: list[UserRatingOut] = []

    model_config = {'from_attributes': True}


class AdminCalendarEntryOut(BaseModel):
    id: int
    year: int
    day: int
    unlock_date: datetime
    title: str
    content: str
    image_url: str | None
    beer_entry_id: int | None
    beer: AdminCalendarBeerOut | None = None

    model_config = {'from_attributes': True}


class CalendarEntryCreate(BaseModel):
    year: int
    day: int
    unlock_date: datetime
    title: str
    content: str
    image_url: str | None = None


class CalendarEntryUpdate(BaseModel):
    unlock_date: datetime | None = None
    title: str | None = None
    content: str | None = None
    image_url: str | None = None


class CalendarBeerAssign(BaseModel):
    beer_entry_id: int
