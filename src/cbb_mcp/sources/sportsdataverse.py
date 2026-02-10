"""sportsdataverse package adapter for historical data."""

import structlog

from cbb_mcp.models.games import (
    BoxScore,
    Game,
    Play,
    PlayerBoxScore,
    PlayByPlay,
    TeamBoxScore,
    TeamScore,
)
from cbb_mcp.models.teams import Team
from cbb_mcp.sources.base import DataCapability, DataSource
from cbb_mcp.utils.constants import CURRENT_SEASON
from cbb_mcp.utils.errors import SourceError

logger = structlog.get_logger()

_sdv = None


def _get_sdv():
    global _sdv
    if _sdv is None:
        try:
            import sportsdataverse.mbb as mbb
            _sdv = mbb
        except ImportError:
            logger.warning("sportsdataverse not installed")
            raise SourceError("sportsdataverse", "Package not installed")
    return _sdv


class SportsdataverseSource(DataSource):
    name = "sportsdataverse"
    priority = 3

    def capabilities(self) -> set[DataCapability]:
        return {
            DataCapability.LIVE_SCORES,
            DataCapability.SCHEDULE,
            DataCapability.BOX_SCORE,
            DataCapability.PLAY_BY_PLAY,
            DataCapability.TEAM_INFO,
        }

    async def get_live_scores(
        self, date: str, conference: str = "", top25: bool = False
    ) -> list[Game]:
        try:
            mbb = _get_sdv()
            import asyncio
            df = await asyncio.to_thread(mbb.espn_mbb_scoreboard, dates=date.replace("-", ""))
        except SourceError:
            raise
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch scores: {e}") from e

        if df is None or df.empty:
            return []

        games: list[Game] = []
        for _, row in df.iterrows():
            games.append(
                Game(
                    id=str(row.get("game_id", "")),
                    date=str(row.get("game_date", "")),
                    status=str(row.get("status_type_state", "post")),
                    status_detail=str(row.get("status_type_detail", "")),
                    home=TeamScore(
                        team_id=str(row.get("home_id", "")),
                        team_name=str(row.get("home_name", row.get("home_display_name", ""))),
                        abbreviation=str(row.get("home_abbreviation", "")),
                        score=int(row.get("home_score", 0) or 0),
                    ),
                    away=TeamScore(
                        team_id=str(row.get("away_id", "")),
                        team_name=str(row.get("away_name", row.get("away_display_name", ""))),
                        abbreviation=str(row.get("away_abbreviation", "")),
                        score=int(row.get("away_score", 0) or 0),
                    ),
                )
            )
        return games

    async def get_schedule(self, team_id: str, season: int = 0) -> list[Game]:
        season = season or CURRENT_SEASON
        try:
            mbb = _get_sdv()
            import asyncio
            df = await asyncio.to_thread(
                mbb.espn_mbb_schedule, dates=str(season)
            )
        except SourceError:
            raise
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch schedule: {e}") from e

        if df is None or df.empty:
            return []

        games: list[Game] = []
        for _, row in df.iterrows():
            home_id = str(row.get("home_id", ""))
            away_id = str(row.get("away_id", ""))
            if team_id and team_id not in (home_id, away_id):
                continue
            games.append(
                Game(
                    id=str(row.get("game_id", "")),
                    date=str(row.get("game_date", "")),
                    status=str(row.get("status_type_state", "")),
                    home=TeamScore(
                        team_id=home_id,
                        team_name=str(row.get("home_display_name", "")),
                        score=int(row.get("home_score", 0) or 0),
                    ),
                    away=TeamScore(
                        team_id=away_id,
                        team_name=str(row.get("away_display_name", "")),
                        score=int(row.get("away_score", 0) or 0),
                    ),
                )
            )
        return games

    async def get_box_score(self, game_id: str) -> BoxScore:
        try:
            mbb = _get_sdv()
            import asyncio
            df = await asyncio.to_thread(
                mbb.espn_mbb_game_rosters, game_id=int(game_id)
            )
        except SourceError:
            raise
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch box score: {e}") from e

        if df is None or df.empty:
            return BoxScore(game=Game(id=game_id))

        # Group by team (home_away field)
        box = BoxScore(game=Game(id=game_id))
        for team_side in ["home", "away"]:
            team_df = df[df.get("home_away", df.get("homeAway", "")) == team_side] if "home_away" in df.columns or "homeAway" in df.columns else df
            if team_df.empty:
                continue

            players: list[PlayerBoxScore] = []
            for _, row in team_df.iterrows():
                players.append(
                    PlayerBoxScore(
                        player_id=str(row.get("athlete_id", "")),
                        name=str(row.get("athlete_display_name", "")),
                        position=str(row.get("athlete_position_abbreviation", "")),
                    )
                )

            team_box = TeamBoxScore(
                team_name=str(team_df.iloc[0].get("team_display_name", "")) if not team_df.empty else "",
                players=players,
            )
            if team_side == "home":
                box.home = team_box
            else:
                box.away = team_box

        return box

    async def get_play_by_play(self, game_id: str) -> PlayByPlay:
        try:
            mbb = _get_sdv()
            import asyncio
            df = await asyncio.to_thread(
                mbb.espn_mbb_pbp, game_id=int(game_id)
            )
        except SourceError:
            raise
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch PBP: {e}") from e

        if df is None or df.empty:
            return PlayByPlay(game=Game(id=game_id))

        plays: list[Play] = []
        for i, (_, row) in enumerate(df.iterrows()):
            plays.append(
                Play(
                    id=str(row.get("id", i)),
                    sequence=i,
                    period=int(row.get("period_number", row.get("period", 0)) or 0),
                    clock=str(row.get("clock_display_value", row.get("clock", ""))),
                    description=str(row.get("text", "")),
                    team_id=str(row.get("team_id", "")),
                    score_home=int(row.get("home_score", 0) or 0),
                    score_away=int(row.get("away_score", 0) or 0),
                    scoring_play=bool(row.get("scoring_play", False)),
                    coordinate_x=float(row["coordinate_x"]) if row.get("coordinate_x") else None,
                    coordinate_y=float(row["coordinate_y"]) if row.get("coordinate_y") else None,
                )
            )

        return PlayByPlay(game=Game(id=game_id), plays=plays)
