
from functools import lru_cache
from typing import Literal

from sqlalchemy import Engine
from sqlalchemy.engine import create_engine

from brobier.core.config import get_settings

DatabaseRole = Literal['app', 'admin']


@lru_cache
def get_engine(role: DatabaseRole = 'app') -> Engine:
    settings = get_settings()
    database_url = settings.app_database_url if role == 'app' else settings.admin_database_url
    engine = create_engine(url=database_url)
    return engine


def get_app_engine() -> Engine:
    return get_engine(role='app')


def get_admin_engine() -> Engine:
    return get_engine(role='admin')
