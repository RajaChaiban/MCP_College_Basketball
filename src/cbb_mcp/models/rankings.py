"""Rankings and standings models."""

from pydantic import BaseModel, Field


class RankedTeam(BaseModel):
    rank: int = 0
    team_id: str = ""
    team_name: str = ""
    conference: str = ""
    record: str = ""
    points: int = 0
    previous_rank: int = 0
    trend: str = ""  # "up", "down", "same", "new"


class Poll(BaseModel):
    name: str = ""  # "AP Top 25", "Coaches Poll", "NET Rankings"
    season: int = 0
    week: int = 0
    date: str = ""
    teams: list[RankedTeam] = Field(default_factory=list)


class StandingsEntry(BaseModel):
    team_id: str = ""
    team_name: str = ""
    conference_rank: int = 0
    overall_record: str = ""
    conference_record: str = ""
    streak: str = ""  # "W3", "L1"
    last_10: str = ""


class ConferenceStandings(BaseModel):
    conference: str = ""
    season: int = 0
    teams: list[StandingsEntry] = Field(default_factory=list)
