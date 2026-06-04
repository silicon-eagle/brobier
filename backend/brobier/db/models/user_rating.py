from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from brobier.db.models.base import Base
from brobier.db.utils import Table

if TYPE_CHECKING:
    from brobier.db.models.beer_entry import BeerEntry
    from brobier.db.models.user import User


class UserRating(Base):
    __tablename__ = Table.user_ratings

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(f'{Table.users}.id'), nullable=False)
    beer_entry_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{Table.beer_entries}.id'), nullable=False)
    rating: Mapped[float | int] = mapped_column(Float, nullable=False)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)
    drank_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship('User', back_populates='user_ratings')
    beer_entry: Mapped[BeerEntry] = relationship('BeerEntry', back_populates='user_ratings')

    __table_args__ = (
        CheckConstraint('rating >= 1.0 AND rating <= 5.0', name='ck_user_ratings_rating'),
        UniqueConstraint('user_id', 'beer_entry_id', name='uq_user_ratings_user_beer'),
    )
