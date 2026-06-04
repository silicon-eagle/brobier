from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from brobier.db.models.base import Base
from brobier.db.utils import Table

if TYPE_CHECKING:
    from brobier.db.models.calendar_entry import CalendarEntry
    from brobier.db.models.user import User
    from brobier.db.models.user_rating import UserRating


class BeerEntry(Base):
    __tablename__ = Table.beer_entries

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(f'{Table.users}.id'), nullable=False)
    beer_name_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    brewery_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    untappd_url_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    comment_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    bought_from: Mapped[str] = mapped_column(String, nullable=False)
    bought_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship('User', back_populates='beer_entries')
    calendar_entry: Mapped[CalendarEntry] = relationship('CalendarEntry', back_populates='beer_entry', uselist=False)
    user_ratings: Mapped[list[UserRating]] = relationship('UserRating', back_populates='beer_entry')
