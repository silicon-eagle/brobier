from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    display_name: str
    beer_count: int
