"""cbbpy package adapter for box scores and play-by-play."""

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
from cbb_mcp.sources.base import DataCapability, DataSource
from cbb_mcp.utils.errors import SourceError

logger = structlog.get_logger()

_cbbpy = None


def _get_cbbpy():
    global _cbbpy
    if _cbbpy is None:
        try:
            import cbbpy.mens_scraper as ms
            _cbbpy = ms
        except ImportError:
            logger.warning("cbbpy not installed")
            raise SourceError("cbbpy", "Package not installed")
    return _cbbpy


class CbbpySource(DataSource):
    name = "cbbpy"
    priority = 4

    def capabilities(self) -> set[DataCapability]:
        return {
            DataCapability.LIVE_SCORES,
            DataCapability.BOX_SCORE,
            DataCapability.PLAY_BY_PLAY,
            DataCapability.SCHEDULE,
        }

    async def get_live_scores(
        self, date: str, conference: str = "", top25: bool = False
    ) -> list[Game]:
        try:
            ms = _get_cbbpy()
            import asyncio
            # cbbpy uses MM/DD/YYYY format
            parts = date.split("-")
            formatted = f"{parts[1]}/{parts[2]}/{parts[0]}" if len(parts) == 3 else date
            info_df, box_df, pbp_df = await asyncio.to_thread(
                ms.get_games_range, formatted, formatted
            )
        except SourceError:
            raise
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch scores: {e}") from e

        if info_df is None or info_df.empty:
            return []

        games: list[Game] = []
        for _, row in info_df.iterrows():
            status = "post" if row.get("FINAL", False) else "pre"
            games.append(
                Game(
                    id=str(row.get("GAME_ID", "")),
                    date=str(row.get("GAME_DAY", "")),
                    status=status,
                    status_detail="Final" if status == "post" else "",
                    venue=str(row.get("ARENA", "")),
                    home=TeamScore(
                        team_name=str(row.get("HOME", "")),
                        score=int(row.get("HOME_SCORE", 0) or 0),
                    ),
                    away=TeamScore(
                        team_name=str(row.get("AWAY", "")),
                        score=int(row.get("AWAY_SCORE", 0) or 0),
                    ),
                )
            )
        return games

    async def get_box_score(self, game_id: str) -> BoxScore:
        try:
            ms = _get_cbbpy()
            import asyncio
            info, box_df, _ = await asyncio.to_thread(ms.get_game, game_id)
        except SourceError:
            raise
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch box score: {e}") from e

        if box_df is None or box_df.empty:
            return BoxScore(game=Game(id=game_id))

        game = Game(id=game_id)

        # Group by team
        teams = box_df["TEAM"].unique() if "TEAM" in box_df.columns else []
        home_box = TeamBoxScore()
        away_box = TeamBoxScore()

        for i, team_name in enumerate(teams):
            team_df = box_df[box_df["TEAM"] == team_name]
            players: list[PlayerBoxScore] = []

            for _, row in team_df.iterrows():
                players.append(
                    PlayerBoxScore(
                        name=str(row.get("PLAYER", "")),
                        position=str(row.get("POS", "")),
                        minutes=str(row.get("MIN", "0")),
                        points=int(row.get("PTS", 0) or 0),
                        rebounds=int(row.get("REB", row.get("TREB", 0)) or 0),
                        assists=int(row.get("AST", 0) or 0),
                        steals=int(row.get("STL", 0) or 0),
                        blocks=int(row.get("BLK", 0) or 0),
                        turnovers=int(row.get("TO", 0) or 0),
                        fouls=int(row.get("PF", 0) or 0),
                    )
                )

            team_box = TeamBoxScore(team_name=str(team_name), players=players)
            if i == 0:
                away_box = team_box
            else:
                home_box = team_box

        return BoxScore(game=game, home=home_box, away=away_box)

    async def get_play_by_play(self, game_id: str) -> PlayByPlay:
        try:
            ms = _get_cbbpy()
            import asyncio
            _, _, pbp_df = await asyncio.to_thread(ms.get_game, game_id)
        except SourceError:
            raise
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch PBP: {e}") from e

        if pbp_df is None or pbp_df.empty:
            return PlayByPlay(game=Game(id=game_id))

        plays: list[Play] = []
        for i, (_, row) in enumerate(pbp_df.iterrows()):
            plays.append(
                Play(
                    sequence=i,
                    period=int(row.get("HALF", row.get("PERIOD", 0)) or 0),
                    clock=str(row.get("TIME_REMAINING", row.get("CLOCK", ""))),
                    description=str(row.get("DESCRIPTION", row.get("PLAY_DESC", ""))),
                    score_home=int(row.get("HOME_SCORE", 0) or 0),
                    score_away=int(row.get("AWAY_SCORE", 0) or 0),
                    scoring_play=bool(row.get("SCORING_PLAY", False)),
                )
            )

        return PlayByPlay(game=Game(id=game_id), plays=plays)
