"""Tests for the NCAA source adapter."""

import pytest
from unittest.mock import AsyncMock, patch

from cbb_mcp.sources.ncaa import NCAASource
from cbb_mcp.sources.base import DataCapability


@pytest.fixture
def ncaa():
    return NCAASource()


def test_capabilities(ncaa):
    caps = ncaa.capabilities()
    assert DataCapability.LIVE_SCORES in caps
    assert DataCapability.RANKINGS in caps


def test_priority(ncaa):
    assert ncaa.priority == 2
    assert ncaa.name == "ncaa"


@pytest.mark.asyncio
async def test_get_live_scores_parses(ncaa):
    mock_data = {
        "games": [
            {
                "game": {
                    "gameID": "6012345",
                    "startDate": "2025-02-09T19:00:00",
                    "gameState": "final",
                    "currentPeriod": "FINAL",
                    "contestClock": "0:00",
                    "venue": {"name": "Cameron Indoor"},
                    "network": "ESPN",
                    "home": {
                        "names": {"full": "Duke Blue Devils", "short": "Duke", "seo": "duke"},
                        "score": "85",
                        "rank": "5",
                    },
                    "away": {
                        "names": {"full": "North Carolina Tar Heels", "short": "UNC", "seo": "north-carolina"},
                        "score": "72",
                        "rank": "12",
                    },
                }
            }
        ]
    }

    with patch("cbb_mcp.sources.ncaa.fetch_json", new_callable=AsyncMock, return_value=mock_data):
        games = await ncaa.get_live_scores("2025-02-09")

    assert len(games) == 1
    g = games[0]
    assert g.id == "6012345"
    assert g.home.team_name == "Duke Blue Devils"
    assert g.home.score == 85
    assert g.home.rank == 5
    assert g.away.team_name == "North Carolina Tar Heels"
    assert g.away.score == 72
    assert g.status == "post"


@pytest.mark.asyncio
async def test_get_rankings_parses(ncaa):
    mock_data = {
        "rankings": [
            {
                "pollName": "AP Top 25",
                "ranks": [
                    {
                        "rank": 1,
                        "previousRank": 1,
                        "votes": 1575,
                        "record": "22-1",
                        "school": {"teamId": "2", "name": "Auburn"},
                        "conference": "SEC",
                    },
                ],
            }
        ]
    }

    with patch("cbb_mcp.sources.ncaa.fetch_json", new_callable=AsyncMock, return_value=mock_data):
        poll = await ncaa.get_rankings("ap")

    assert len(poll.teams) == 1
    assert poll.teams[0].rank == 1
    assert poll.teams[0].team_name == "Auburn"
    assert poll.teams[0].trend == "same"
