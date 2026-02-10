"""Abstract base class and capability enum for data sources."""

from abc import ABC, abstractmethod
from enum import Enum, auto

from cbb_mcp.models.games import BoxScore, Game, PlayByPlay
from cbb_mcp.models.rankings import ConferenceStandings, Poll
from cbb_mcp.models.stats import PlayerStats, StatLeader, TeamStats
from cbb_mcp.models.teams import Player, Team


class DataCapability(Enum):
    LIVE_SCORES = auto()
    TEAM_INFO = auto()
    TEAM_SEARCH = auto()
    ROSTER = auto()
    SCHEDULE = auto()
    GAME_DETAIL = auto()
    BOX_SCORE = auto()
    PLAY_BY_PLAY = auto()
    RANKINGS = auto()
    STANDINGS = auto()
    TEAM_STATS = auto()
    PLAYER_STATS = auto()
    STAT_LEADERS = auto()
    TOURNAMENT = auto()


class DataSource(ABC):
    """Abstract base for all data sources."""

    name: str = "base"
    priority: int = 0  # lower = higher priority

    @abstractmethod
    def capabilities(self) -> set[DataCapability]:
        """Return the set of capabilities this source provides."""
        ...

    async def get_live_scores(self, date: str, conference: str = "", top25: bool = False) -> list[Game]:
        raise NotImplementedError

    async def get_team(self, team_id: str) -> Team:
        raise NotImplementedError

    async def search_teams(self, query: str, conference: str = "") -> list[Team]:
        raise NotImplementedError

    async def get_roster(self, team_id: str) -> list[Player]:
        raise NotImplementedError

    async def get_schedule(self, team_id: str, season: int = 0) -> list[Game]:
        raise NotImplementedError

    async def get_game_detail(self, game_id: str) -> Game:
        raise NotImplementedError

    async def get_box_score(self, game_id: str) -> BoxScore:
        raise NotImplementedError

    async def get_play_by_play(self, game_id: str) -> PlayByPlay:
        raise NotImplementedError

    async def get_rankings(self, poll_type: str = "ap", season: int = 0, week: int = 0) -> Poll:
        raise NotImplementedError

    async def get_standings(self, conference: str = "") -> list[ConferenceStandings]:
        raise NotImplementedError

    async def get_team_stats(self, team_id: str, season: int = 0) -> TeamStats:
        raise NotImplementedError

    async def get_player_stats(self, player_id: str = "", team_id: str = "") -> list[PlayerStats]:
        raise NotImplementedError

    async def get_stat_leaders(self, category: str = "scoring", season: int = 0) -> list[StatLeader]:
        raise NotImplementedError
