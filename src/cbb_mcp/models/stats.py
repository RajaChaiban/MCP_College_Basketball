"""Statistics models."""

from pydantic import BaseModel, Field


class TeamStats(BaseModel):
    team_id: str = ""
    team_name: str = ""
    season: int = 0
    games_played: int = 0
    ppg: float = 0.0
    opp_ppg: float = 0.0
    fg_pct: float = 0.0
    three_pct: float = 0.0
    ft_pct: float = 0.0
    rpg: float = 0.0
    apg: float = 0.0
    spg: float = 0.0
    bpg: float = 0.0
    topg: float = 0.0
    offensive_rpg: float = 0.0
    defensive_rpg: float = 0.0


class PlayerStats(BaseModel):
    player_id: str = ""
    name: str = ""
    team: str = ""
    position: str = ""
    games_played: int = 0
    minutes_per_game: float = 0.0
    ppg: float = 0.0
    rpg: float = 0.0
    apg: float = 0.0
    spg: float = 0.0
    bpg: float = 0.0
    topg: float = 0.0
    fg_pct: float = 0.0
    three_pct: float = 0.0
    ft_pct: float = 0.0


class StatLeader(BaseModel):
    rank: int = 0
    player_id: str = ""
    name: str = ""
    team: str = ""
    value: float = 0.0
    stat_category: str = ""


class TeamComparison(BaseModel):
    team1: TeamStats = Field(default_factory=TeamStats)
    team2: TeamStats = Field(default_factory=TeamStats)
    advantages: dict[str, str] = Field(default_factory=dict)
