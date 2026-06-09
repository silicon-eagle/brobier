from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from brobier.db.engine import get_app_engine
from brobier.db.models import BeerEntry, User
from brobier.schemas.leaderboard import LeaderboardEntry

router = APIRouter(tags=['leaderboard'])


@router.get('', response_model=list[LeaderboardEntry])
def get_leaderboard() -> list[LeaderboardEntry]:
    with Session(get_app_engine()) as db:
        rows = db.execute(
            select(User.display_name, func.count(BeerEntry.id).label('beer_count'))
            .join(BeerEntry, BeerEntry.user_id == User.id)
            .group_by(User.id, User.display_name)
            .order_by(func.count(BeerEntry.id).desc())
        ).all()
        return [LeaderboardEntry(display_name=row.display_name, beer_count=row.beer_count) for row in rows]
