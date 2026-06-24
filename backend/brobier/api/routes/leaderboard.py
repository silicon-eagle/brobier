from fastapi import APIRouter

from brobier.schemas.leaderboard import LeaderboardEntry
from brobier.services import leaderboard_service

router = APIRouter(tags=['leaderboard'])


@router.get('', response_model=list[LeaderboardEntry])
def get_leaderboard(year: int | None = None) -> list[LeaderboardEntry]:
    return leaderboard_service.list_leaderboard(year)
