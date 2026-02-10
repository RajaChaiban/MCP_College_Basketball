"""Tests for the ESPN source adapter."""

import pytest
from unittest.mock import AsyncMock, patch

from cbb_mcp.sources.espn import ESPNSource
from cbb_mcp.sources.base import DataCapability


@pytest.fixture
def espn():
    return ESPNSource()


def test_capabilities(espn):
    caps = espn.capabilities()
    assert DataCapability.LIVE_SCORES in caps
    assert DataCapability.TEAM_INFO in caps
    assert DataCapability.RANKINGS in caps
    assert DataCapability.BOX_SCORE in caps
    assert DataCapability.PLAY_BY_PLAY in caps
    assert DataCapability.STANDINGS in caps
    assert DataCapability.TEAM_STATS in caps


def test_priority(espn):
    assert espn.priority == 1
    assert espn.name == "espn"


@pytest.mark.asyncio
async def test_get_live_scores_parses(espn):
    mock_data = {
        "events": [
            {
                "id": "401720001",
                "date": "2025-02-09T00:00Z",
                "competitions": [
                    {
                        "status": {"type": {"state": "post", "detail": "Final"}},
                        "competitors": [
                            {
                                "homeAway": "home",
                                "team": {"id": "150", "displayName": "Duke Blue Devils", "abbreviation": "DUKE"},
                                "score": "85",
                                "curatedRank": {"current": 5},
                                "records": [{"summary": "20-3"}],
                            },
                            {
                                "homeAway": "away",
                                "team": {"id": "153", "displayName": "North Carolina Tar Heels", "abbreviation": "UNC"},
                                "score": "72",
                                "curatedRank": {"current": 12},
                                "records": [{"summary": "17-6"}],
                            },
                        ],
                        "venue": {"fullName": "Cameron Indoor Stadium"},
                        "broadcasts": [{"names": ["ESPN"]}],
                        "notes": [],
                    }
                ],
            }
        ]
    }

    with patch("cbb_mcp.sources.espn.fetch_json", new_callable=AsyncMock, return_value=mock_data):
        games = await espn.get_live_scores("2025-02-09")

    assert len(games) == 1
    g = games[0]
    assert g.id == "401720001"
    assert g.home.team_name == "Duke Blue Devils"
    assert g.home.score == 85
    assert g.home.rank == 5
    assert g.away.team_name == "North Carolina Tar Heels"
    assert g.away.score == 72
    assert g.away.rank == 12
    assert g.status == "post"


@pytest.mark.asyncio
async def test_get_live_scores_top25_filter(espn):
    mock_data = {
        "events": [
            {
                "id": "1",
                "date": "2025-02-09T00:00Z",
                "competitions": [{
                    "status": {"type": {"state": "post", "detail": "Final"}},
                    "competitors": [
                        {"homeAway": "home", "team": {"id": "1", "displayName": "Team A"}, "score": "70", "curatedRank": {"current": 99}},
                        {"homeAway": "away", "team": {"id": "2", "displayName": "Team B"}, "score": "60", "curatedRank": {"current": 99}},
                    ],
                    "venue": {},
                    "broadcasts": [],
                    "notes": [],
                }],
            },
            {
                "id": "2",
                "date": "2025-02-09T00:00Z",
                "competitions": [{
                    "status": {"type": {"state": "post", "detail": "Final"}},
                    "competitors": [
                        {"homeAway": "home", "team": {"id": "3", "displayName": "Ranked Team"}, "score": "80", "curatedRank": {"current": 3}},
                        {"homeAway": "away", "team": {"id": "4", "displayName": "Other"}, "score": "60", "curatedRank": {"current": 99}},
                    ],
                    "venue": {},
                    "broadcasts": [],
                    "notes": [],
                }],
            },
        ]
    }

    with patch("cbb_mcp.sources.espn.fetch_json", new_callable=AsyncMock, return_value=mock_data):
        games = await espn.get_live_scores("2025-02-09", top25=True)

    assert len(games) == 1
    assert games[0].home.rank == 3


@pytest.mark.asyncio
async def test_get_rankings_parses(espn):
    mock_data = {
        "rankings": [
            {
                "name": "AP Top 25",
                "week": 14,
                "date": "2025-02-10",
                "ranks": [
                    {
                        "current": 1,
                        "previous": 1,
                        "points": 1575,
                        "recordSummary": "22-1",
                        "team": {"id": "2", "nickname": "Auburn", "conference": "SEC"},
                    },
                    {
                        "current": 2,
                        "previous": 3,
                        "points": 1520,
                        "recordSummary": "21-2",
                        "team": {"id": "150", "nickname": "Duke", "conference": "ACC"},
                    },
                ],
            }
        ]
    }

    with patch("cbb_mcp.sources.espn.fetch_json", new_callable=AsyncMock, return_value=mock_data):
        poll = await espn.get_rankings("ap")

    assert poll.name == "AP Top 25"
    assert len(poll.teams) == 2
    assert poll.teams[0].rank == 1
    assert poll.teams[0].team_name == "Auburn"
    assert poll.teams[0].trend == "same"
    assert poll.teams[1].rank == 2
    assert poll.teams[1].trend == "up"


@pytest.mark.asyncio
async def test_search_teams(espn):
    mock_data = {
        "sports": [{"leagues": [{"teams": [
            {"team": {"id": "150", "displayName": "Duke Blue Devils", "abbreviation": "DUKE", "nickname": "Blue Devils", "location": "Duke"}},
            {"team": {"id": "153", "displayName": "North Carolina Tar Heels", "abbreviation": "UNC", "nickname": "Tar Heels", "location": "North Carolina"}},
            {"team": {"id": "248", "displayName": "Duquesne Dukes", "abbreviation": "DUQ", "nickname": "Dukes", "location": "Duquesne"}},
        ]}]}]
    }

    with patch("cbb_mcp.sources.espn.fetch_json", new_callable=AsyncMock, return_value=mock_data):
        result = await espn.search_teams("duke")

    assert len(result) >= 1
    names = [t.name for t in result]
    assert "Duke Blue Devils" in names
