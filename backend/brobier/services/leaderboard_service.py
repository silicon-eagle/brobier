from sqlalchemy import func, select
from sqlalchemy.orm import Session

from brobier.core.time import current_time
from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, User
from brobier.db.models.user import UserRole
from brobier.schemas.leaderboard import LeaderboardEntry


def list_leaderboard(year: int | None = None) -> list[LeaderboardEntry]:
    effective_year = year or current_time().year
    beer_count = func.count(BeerEntry.id).label('beer_count')

    with Session(get_app_engine()) as db:
        rows = db.execute(
            select(User.display_name, beer_count)
            .outerjoin(BeerEntry, (BeerEntry.user_id == User.id) & (BeerEntry.year == effective_year))
            .filter(User.role != UserRole.admin)
            .group_by(User.id, User.display_name)
            .order_by(beer_count.desc(), User.display_name)
        ).all()
        return [LeaderboardEntry(display_name=row.display_name, beer_count=row.beer_count) for row in rows]
