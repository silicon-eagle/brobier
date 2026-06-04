import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserRatingCreate(BaseModel):
    rating: float = Field(ge=1.0, le=5.0)
    comment: str | None = None
    drank_at: datetime | None = None


class UserRatingUpdate(BaseModel):
    rating: float | None = Field(default=None, ge=1.0, le=5.0)
    comment: str | None = None
    drank_at: datetime | None = None


class UserRatingOut(BaseModel):
    id: int
    user_id: uuid.UUID
    beer_entry_id: int
    rating: float
    comment: str | None
    drank_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}
