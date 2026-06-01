from fastapi import APIRouter, HTTPException, status

from backend.schemas.leaderboard import LeaderboardEntry

router = APIRouter(tags=['leaderboard'])


@router.get('', response_model=list[LeaderboardEntry])
def get_leaderboard() -> list[LeaderboardEntry]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Not implemented.')
