"""Game-related models."""

from datetime import datetime
from pydantic import BaseModel, Field


class TeamScore(BaseModel):
    team_id: str = ""
    team_name: str = ""
    abbreviation: str = ""
    score: int = 0
    rank: int | None = None
    record: str = ""
    logo_url: str = ""
    line_scores: list[int] = Field(default_factory=list)  # per-half or per-period scores

    @property
    def display_name(self) -> str:
        rank_prefix = f"#{self.rank} " if self.rank else ""
        return f"{rank_prefix}{self.team_name}"


class Game(BaseModel):
    id: str = ""
    date: str = ""  # ISO datetime string
    status: str = ""  # pre, in, post
    status_detail: str = ""  # e.g. "Final", "Halftime", "2nd Half 12:34"
    period: int = 0
    clock: str = ""
    venue: str = ""
    broadcast: str = ""
    conference_game: bool = False
    neutral_site: bool = False
    home: TeamScore = Field(default_factory=TeamScore)
    away: TeamScore = Field(default_factory=TeamScore)
    notes: str = ""  # tournament round info, etc.

    @property
    def final_score(self) -> str:
        return f"{self.away.display_name} {self.away.score} - {self.home.score} {self.home.display_name}"


class PlayerBoxScore(BaseModel):
    player_id: str = ""
    name: str = ""
    position: str = ""
    minutes: str = ""
    points: int = 0
    rebounds: int = 0
    assists: int = 0
    steals: int = 0
    blocks: int = 0
    turnovers: int = 0
    fouls: int = 0
    fgm: int = 0
    fga: int = 0
    fg_pct: float = 0.0
    tpm: int = 0
    tpa: int = 0
    tp_pct: float = 0.0
    ftm: int = 0
    fta: int = 0
    ft_pct: float = 0.0
    offensive_rebounds: int = 0
    defensive_rebounds: int = 0


class TeamBoxScore(BaseModel):
    team_id: str = ""
    team_name: str = ""
    players: list[PlayerBoxScore] = Field(default_factory=list)
    totals: PlayerBoxScore = Field(default_factory=PlayerBoxScore)


class BoxScore(BaseModel):
    game: Game = Field(default_factory=Game)
    home: TeamBoxScore = Field(default_factory=TeamBoxScore)
    away: TeamBoxScore = Field(default_factory=TeamBoxScore)


class Play(BaseModel):
    id: str = ""
    sequence: int = 0
    period: int = 0
    clock: str = ""
    description: str = ""
    team_id: str = ""
    score_home: int = 0
    score_away: int = 0
    scoring_play: bool = False
    shot_type: str = ""
    coordinate_x: float | None = None
    coordinate_y: float | None = None


class PlayByPlay(BaseModel):
    game: Game = Field(default_factory=Game)
    plays: list[Play] = Field(default_factory=list)
