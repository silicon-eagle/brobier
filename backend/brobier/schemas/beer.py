import uuid
from datetime import datetime

from pydantic import BaseModel


class BeerEntryCreate(BaseModel):
    year: int
    beer_name: str
    brewery: str
    untappd_url: str | None = None
    comment: str | None = None
    bought_from: str
    bought_at: datetime


class BeerEntryUpdate(BaseModel):
    year: int | None = None
    beer_name: str | None = None
    brewery: str | None = None
    untappd_url: str | None = None
    comment: str | None = None
    bought_from: str | None = None
    bought_at: datetime | None = None


class BeerEntryOut(BaseModel):
    id: int
    user_id: uuid.UUID
    year: int
    beer_name: str
    brewery: str
    untappd_url: str | None
    comment: str | None
    bought_from: str
    bought_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}
