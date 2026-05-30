from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.db.models.calendar_entry import CalendarEntry
from backend.db.models.user import User, UserRole
from backend.db.utils import Table


def _is_users_seeded(db: Session) -> bool:
    return db.query(User).first() is not None


def _is_calendar_seeded(db: Session) -> bool:
    year = datetime.now().year
    return db.query(CalendarEntry).filter(CalendarEntry.year == year).first() is not None


def _seed_users(db: Session) -> None:
    db.add_all([
        User(email='admin@brobier.local', display_name='Admin', role=UserRole.admin, is_active=True),
        User(email='alice@brobier.local', display_name='Alice', role=UserRole.user, is_active=True),
        User(email='bob@brobier.local', display_name='Bob', role=UserRole.user, is_active=True),
        User(email='carol@brobier.local', display_name='Carol', role=UserRole.user, is_active=True),
        User(email='dave@brobier.local', display_name='Dave', role=UserRole.user, is_active=False),
    ])


def _seed_calendar(db: Session) -> None:
    year = datetime.now().year
    existing_days = {
        row.day
        for row in db.query(CalendarEntry.day).filter(CalendarEntry.year == year).all()
    }
    db.add_all([
        CalendarEntry(
            year=year,
            day=day,
            unlock_date=datetime(year, 12, day, 8, 0, 0, tzinfo=UTC),
            title=f'Day {day}',
            content='',
        )
        for day in range(1, 25)
        if day not in existing_days
    ])


seeders: list[tuple[Table, Callable[[Session], bool], Callable[[Session], None]]] = [
    (Table.users, _is_users_seeded, _seed_users),
    (Table.calendar_entries, _is_calendar_seeded, _seed_calendar),
]

def seed_database(engine: Engine, tables: list[Table] | None = None) -> None:
    with Session(engine) as db:
        for table, is_seeded, seed in seeders:
            if tables is not None and table.value not in tables:
                if not is_seeded(db):
                    seed(db)
        db.commit()

def check_is_seeded(engine: Engine, tables: list[Table] | None = None) -> dict[Table, bool]:
    result = {}
    with Session(engine) as db:
        for table, is_seeded, _ in seeders:
            if tables is not None and table.value not in tables:
                result[table] = is_seeded(db)
    return result
