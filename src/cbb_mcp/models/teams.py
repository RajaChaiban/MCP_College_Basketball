"""Team-related models."""

from pydantic import BaseModel, Field
from .common import Record, Venue


class Team(BaseModel):
    id: str = ""
    name: str = ""
    abbreviation: str = ""
    mascot: str = ""
    conference: str = ""
    logo_url: str = ""
    color: str = ""
    record: Record = Field(default_factory=Record)
    rank: int | None = None
    venue: Venue = Field(default_factory=Venue)

    @property
    def display_name(self) -> str:
        rank_prefix = f"#{self.rank} " if self.rank else ""
        return f"{rank_prefix}{self.name}"


class Player(BaseModel):
    id: str = ""
    name: str = ""
    jersey: str = ""
    position: str = ""
    height: str = ""
    weight: str = ""
    year: str = ""  # Fr, So, Jr, Sr
    hometown: str = ""


class Roster(BaseModel):
    team: Team = Field(default_factory=Team)
    players: list[Player] = Field(default_factory=list)


class Conference(BaseModel):
    id: str = ""
    name: str = ""
    short_name: str = ""
    teams: list[Team] = Field(default_factory=list)
