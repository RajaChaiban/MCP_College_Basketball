"""NCAA API adapter (henrygd NCAA API)."""

import structlog

from cbb_mcp.models.games import Game, TeamScore
from cbb_mcp.models.rankings import Poll, RankedTeam
from cbb_mcp.models.teams import Team
from cbb_mcp.sources.base import DataCapability, DataSource
from cbb_mcp.utils.constants import CURRENT_SEASON, NCAA_API_BASE
from cbb_mcp.utils.errors import SourceError
from cbb_mcp.utils.http_client import fetch_json

logger = structlog.get_logger()


class NCAASource(DataSource):
    name = "ncaa"
    priority = 2

    def capabilities(self) -> set[DataCapability]:
        return {
            DataCapability.LIVE_SCORES,
            DataCapability.RANKINGS,
            DataCapability.TEAM_INFO,
            DataCapability.GAME_DETAIL,
        }

    async def get_live_scores(
        self, date: str, conference: str = "", top25: bool = False
    ) -> list[Game]:
        # NCAA API format: YYYY/MM/DD
        formatted = date.replace("-", "/")
        try:
            data = await fetch_json(
                f"{NCAA_API_BASE}/scoreboard/basketball-men/d1/{formatted}"
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch scores: {e}") from e

        games: list[Game] = []
        for g in data.get("games", []):
            game_data = g.get("game", g)
            home = game_data.get("home", {})
            away = game_data.get("away", {})

            home_names = home.get("names", {})
            away_names = away.get("names", {})

            game = Game(
                id=str(game_data.get("gameID", "")),
                date=game_data.get("startDate", ""),
                status=self._map_status(game_data.get("gameState", "")),
                status_detail=game_data.get("currentPeriod", game_data.get("gameState", "")),
                period=int(game_data.get("currentPeriod", "0") or "0") if str(game_data.get("currentPeriod", "")).isdigit() else 0,
                clock=game_data.get("contestClock", ""),
                venue=game_data.get("venue", {}).get("name", "") if isinstance(game_data.get("venue"), dict) else "",
                broadcast=game_data.get("network", ""),
                home=TeamScore(
                    team_id=str(home.get("teamId", home.get("school", {}).get("teamId", ""))),
                    team_name=home_names.get("full", home_names.get("short", "")),
                    abbreviation=home_names.get("seo", home_names.get("short", ""))[:6],
                    score=int(home.get("score", 0) or 0),
                    rank=self._parse_rank(home.get("rank")),
                ),
                away=TeamScore(
                    team_id=str(away.get("teamId", away.get("school", {}).get("teamId", ""))),
                    team_name=away_names.get("full", away_names.get("short", "")),
                    abbreviation=away_names.get("seo", away_names.get("short", ""))[:6],
                    score=int(away.get("score", 0) or 0),
                    rank=self._parse_rank(away.get("rank")),
                ),
            )

            if top25 and not (game.home.rank or game.away.rank):
                continue

            games.append(game)
        return games

    async def get_rankings(
        self, poll_type: str = "ap", season: int = 0, week: int = 0
    ) -> Poll:
        season = season or CURRENT_SEASON
        poll_map = {"ap": "AP", "coaches": "coaches", "net": "NET"}
        poll_name = poll_map.get(poll_type.lower(), "AP")

        try:
            data = await fetch_json(
                f"{NCAA_API_BASE}/rankings/basketball-men/d1"
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch rankings: {e}") from e

        ranked_teams: list[RankedTeam] = []
        rankings = data.get("rankings", [])

        # Find the right poll
        target_poll = None
        for poll in rankings:
            if poll_name.lower() in poll.get("pollName", "").lower():
                target_poll = poll
                break

        if not target_poll and rankings:
            target_poll = rankings[0]

        if target_poll:
            for entry in target_poll.get("ranks", []):
                school = entry.get("school", {})
                ranked_teams.append(
                    RankedTeam(
                        rank=int(entry.get("rank", 0)),
                        team_id=str(school.get("teamId", "")),
                        team_name=school.get("name", school.get("fullName", "")),
                        conference=entry.get("conference", ""),
                        record=entry.get("record", ""),
                        points=int(entry.get("votes", entry.get("points", 0)) or 0),
                        previous_rank=int(entry.get("previousRank", 0) or 0),
                        trend=self._calc_trend(
                            int(entry.get("rank", 0)),
                            int(entry.get("previousRank", 0) or 0),
                        ),
                    )
                )

        return Poll(
            name=target_poll.get("pollName", poll_type) if target_poll else poll_type,
            season=season,
            week=week,
            teams=ranked_teams,
        )

    def _map_status(self, state: str) -> str:
        state_map = {"pre": "pre", "live": "in", "final": "post", "F": "post"}
        return state_map.get(state, state)

    def _parse_rank(self, rank) -> int | None:
        if not rank:
            return None
        try:
            r = int(rank)
            return r if 1 <= r <= 25 else None
        except (ValueError, TypeError):
            return None

    def _calc_trend(self, current: int, previous: int) -> str:
        if previous == 0:
            return "new"
        if current < previous:
            return "up"
        if current > previous:
            return "down"
        return "same"
