from collections.abc import Generator

from sqlalchemy.orm import Session

from backend.db.engine import get_engine


def get_db() -> Generator[Session, None, None]:
    with Session(get_engine()) as db:
        yield db
