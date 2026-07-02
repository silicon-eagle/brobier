import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from brobier.db.models.base import Base
from brobier.db.utils import Table

if TYPE_CHECKING:
    from brobier.db.models.user import User


class RefreshToken(Base):
    __tablename__ = Table.refresh_tokens

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey(f'{Table.users}.id'), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped['User'] = relationship('User', back_populates='refresh_tokens')

    __table_args__ = (Index('ix_refresh_tokens_token_hash', 'token_hash'),)
