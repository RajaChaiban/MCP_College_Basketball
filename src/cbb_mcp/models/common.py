"""Shared model types."""

from datetime import date, datetime
from pydantic import BaseModel, Field


class DateRange(BaseModel):
    start: date
    end: date


class Pagination(BaseModel):
    page: int = 1
    per_page: int = 25
    total: int = 0


class Record(BaseModel):
    wins: int = 0
    losses: int = 0
    conference_wins: int = 0
    conference_losses: int = 0

    @property
    def overall(self) -> str:
        return f"{self.wins}-{self.losses}"

    @property
    def conference(self) -> str:
        return f"{self.conference_wins}-{self.conference_losses}"


class Venue(BaseModel):
    name: str = ""
    city: str = ""
    state: str = ""
    capacity: int = 0
