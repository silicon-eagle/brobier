import pytest
from brobier.core.time import current_time
from brobier.schemas.leaderboard import LeaderboardEntry
from brobier.services.leaderboard_service import list_leaderboard


@pytest.mark.usefixtures('database')
class TestLeaderboardService:
    def test_list_leaderboard_returns_all_users_for_current_year_with_zero_counts(self) -> None:
        leaderboard = list_leaderboard(current_time().year)

        assert leaderboard == [
            LeaderboardEntry(display_name='Alice', beer_count=0),
            LeaderboardEntry(display_name='Bob', beer_count=0),
            LeaderboardEntry(display_name='Carol', beer_count=0),
            LeaderboardEntry(display_name='Dave', beer_count=0),
        ]
