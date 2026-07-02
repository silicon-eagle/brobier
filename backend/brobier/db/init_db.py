from sqlalchemy import Engine, inspect

from brobier.core.config import get_settings
from brobier.db.engine import get_admin_engine
from brobier.db.models.base import Base

EXPECTED_TABLES = {'users', 'beer_entries', 'calendar_entries', 'login_codes', 'refresh_tokens', 'user_ratings'}


def tables_exist(engine: Engine) -> bool:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    return EXPECTED_TABLES.issubset(existing)


def db_create(engine: Engine | None = None) -> None:
    active_engine = engine or get_admin_engine()
    Base.metadata.create_all(active_engine)


def db_drop(engine: Engine | None = None) -> None:
    active_engine = engine or get_admin_engine()
    Base.metadata.drop_all(active_engine)


def db_recreate(engine: Engine | None = None) -> None:
    active_engine = engine or get_admin_engine()
    Base.metadata.drop_all(active_engine)
    Base.metadata.create_all(active_engine)


def init_db(engine: Engine | None = None) -> None:
    settings = get_settings()
    active_engine = engine or get_admin_engine()

    if tables_exist(active_engine):
        if settings.db_overwrite:
            db_recreate(active_engine)
    else:
        Base.metadata.create_all(active_engine)
