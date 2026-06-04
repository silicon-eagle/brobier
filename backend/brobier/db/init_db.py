from sqlalchemy import Engine, inspect

from brobier.core.config import get_settings
from brobier.db.models.base import Base

EXPECTED_TABLES = {'users', 'beer_entries', 'calendar_entries', 'login_codes', 'refresh_tokens', 'user_ratings'}


def tables_exist(engine: Engine) -> bool:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    return EXPECTED_TABLES.issubset(existing)


def db_create(engine: Engine) -> None:
    Base.metadata.create_all(engine)

def db_drop(engine: Engine) -> None:
    Base.metadata.drop_all(engine)

def db_recreate(engine: Engine) -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def init_db(engine: Engine) -> None:
    settings = get_settings()

    if tables_exist(engine):
        if settings.db_overwrite:
            db_recreate(engine)
    else:
        Base.metadata.create_all(engine)
