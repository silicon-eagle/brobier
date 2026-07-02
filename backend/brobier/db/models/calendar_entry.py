from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from brobier.db.models.base import Base
from brobier.db.utils import Table

if TYPE_CHECKING:
    from brobier.db.models.beer_entry import BeerEntry


class CalendarEntry(Base):
    __tablename__ = Table.calendar_entries

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    unlock_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    beer_entry_id: Mapped[int | None] = mapped_column(Integer, ForeignKey(f'{Table.beer_entries}.id'), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    beer_entry: Mapped[BeerEntry] = relationship('BeerEntry', back_populates='calendar_entry')

    __table_args__ = (
        UniqueConstraint('year', 'day', name='uq_calendar_entries_year_day'),
        CheckConstraint('year >= 2020', name='ck_calendar_entries_year'),
        CheckConstraint('day >= 1 AND day <= 24', name='ck_calendar_entries_day'),
        Index('ix_calendar_entries_year', 'year'),
    )
