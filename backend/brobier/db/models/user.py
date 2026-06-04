from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from brobier.db.models.base import Base
from brobier.db.utils import Table

if TYPE_CHECKING:
    from brobier.db.models.beer_entry import BeerEntry
    from brobier.db.models.login_code import LoginCode
    from brobier.db.models.refresh_token import RefreshToken
    from brobier.db.models.user_rating import UserRating


class UserRole(enum.StrEnum):
    user = 'user'
    admin = 'admin'


class User(Base):
    __tablename__ = Table.users

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.user)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    beer_entries: Mapped[list[BeerEntry]] = relationship('BeerEntry', back_populates='user')
    login_codes: Mapped[list[LoginCode]] = relationship('LoginCode', back_populates='user')
    refresh_tokens: Mapped[list[RefreshToken]] = relationship('RefreshToken', back_populates='user')
    user_ratings: Mapped[list[UserRating]] = relationship('UserRating', back_populates='user')

    __table_args__ = (Index('ix_users_email', 'email'),)
