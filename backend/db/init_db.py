from sqlalchemy import Engine, inspect

import backend.models  # noqa: F401 — ensures all models are registered with Base.metadata
from backend.core.config import get_settings
from backend.models.base import Base

EXPECTED_TABLES = {'user', 'beer_entry', 'calendar_entry', 'login_code', 'session', 'user_rating'}


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
