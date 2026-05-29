
from sqlalchemy import Engine
from sqlalchemy.engine import create_engine

from backend.core.config import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    engine = create_engine(url=settings.database_url)
    return engine
