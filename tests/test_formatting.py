"""Tests for formatting helpers."""

import pytest

from cbb_mcp.models.games import (
    BoxScore,
    Game,
    PlayerBoxScore,
    TeamBoxScore,
    TeamScore,
)
from cbb_mcp.models.stats import PlayerStats, TeamComparison, TeamStats
from cbb_mcp.utils.formatting import (
    format_box_score,
    format_comparison,
    format_game,
    format_game_detail,
    format_player_stats,
    format_schedule,
    format_team_stats,
)
from cbb_mcp.models.teams import Team
from cbb_mcp.models.common import Record, Venue


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def sample_game() -> Game:
    return Game(
        id="401234567",
        date="2026-02-10T19:00Z",
        status="post",
        status_detail="Final",
        venue="Rupp Arena",
        broadcast="ESPN",
        conference_game=True,
        neutral_site=False,
        period=2,
        clock="0:00",
        home=TeamScore(
            team_id="100",
            team_name="Kentucky",
            abbreviation="UK",
            score=78,
            rank=5,
            record="20-3",
            line_scores=[35, 43],
        ),
        away=TeamScore(
            team_id="200",
            team_name="Florida",
            abbreviation="FLA",
            score=72,
            rank=12,
            record="18-5",
            line_scores=[30, 42],
        ),
    )


@pytest.fixture
def sample_team() -> Team:
    return Team(
        id="200",
        name="Florida",
        abbreviation="FLA",
        conference="SEC",
        record=Record(wins=18, losses=5),
        venue=Venue(name="Exactech Arena"),
    )


@pytest.fixture
def sample_box_score(sample_game: Game) -> BoxScore:
    player = PlayerBoxScore(
        player_id="p1",
        name="John Doe",
        position="G",
        minutes="32",
        points=20,
        rebounds=5,
        assists=4,
        steals=2,
        blocks=1,
        turnovers=3,
        fouls=2,
        fgm=7,
        fga=14,
        fg_pct=50.0,
        tpm=3,
        tpa=6,
        tp_pct=50.0,
        ftm=3,
        fta=4,
        ft_pct=75.0,
    )
    totals = PlayerBoxScore(
        points=78,
        rebounds=35,
        assists=15,
        steals=6,
        blocks=3,
        turnovers=10,
        fouls=14,
        fgm=28,
        fga=55,
        fg_pct=50.9,
        tpm=8,
        tpa=20,
        tp_pct=40.0,
        ftm=14,
        fta=18,
        ft_pct=77.8,
    )
    home_box = TeamBoxScore(
        team_id="100",
        team_name="Kentucky",
        players=[player],
        totals=totals,
    )
    away_box = TeamBoxScore(
        team_id="200",
        team_name="Florida",
        players=[player],
        totals=totals,
    )
    return BoxScore(game=sample_game, home=home_box, away=away_box)


# ── format_game: Game ID ──────────────────────────────────────


class TestFormatGame:
    def test_game_id_appears_in_output(self, sample_game: Game):
        result = format_game(sample_game)
        assert "[Game ID: 401234567]" in result

    def test_no_game_id_when_empty(self):
        game = Game(
            status="post",
            status_detail="Final",
            home=TeamScore(team_name="TeamA", score=70),
            away=TeamScore(team_name="TeamB", score=65),
        )
        result = format_game(game)
        assert "[Game ID:" not in result

    def test_game_id_in_pre_game(self):
        game = Game(
            id="401999999",
            status="pre",
            status_detail="7:00 PM ET",
            home=TeamScore(team_name="Duke"),
            away=TeamScore(team_name="UNC"),
        )
        result = format_game(game)
        assert "[Game ID: 401999999]" in result


# ── format_schedule: Game ID ──────────────────────────────────


class TestFormatSchedule:
    def test_game_id_appears_in_schedule(self, sample_team: Team, sample_game: Game):
        result = format_schedule(sample_team, [sample_game])
        assert "[ID: 401234567]" in result

    def test_no_id_when_empty(self, sample_team: Team):
        game = Game(
            status="post",
            status_detail="Final",
            home=TeamScore(team_id="200", team_name="Florida", score=80),
            away=TeamScore(team_id="300", team_name="Georgia", score=70),
        )
        result = format_schedule(sample_team, [game])
        assert "[ID:" not in result


# ── format_box_score ──────────────────────────────────────────


class TestFormatBoxScore:
    def test_has_3pt_column(self, sample_box_score: BoxScore):
        result = format_box_score(sample_box_score)
        assert "3PT" in result

    def test_has_ft_column(self, sample_box_score: BoxScore):
        result = format_box_score(sample_box_score)
        assert "FT%" in result

    def test_has_to_column(self, sample_box_score: BoxScore):
        result = format_box_score(sample_box_score)
        assert " TO" in result

    def test_has_pf_column(self, sample_box_score: BoxScore):
        result = format_box_score(sample_box_score)
        assert " PF" in result

    def test_has_half_scores(self, sample_box_score: BoxScore):
        result = format_box_score(sample_box_score)
        assert "1st" in result
        assert "2nd" in result

    def test_player_3pt_data(self, sample_box_score: BoxScore):
        result = format_box_score(sample_box_score)
        assert "3-6" in result  # tpm-tpa

    def test_player_ft_data(self, sample_box_score: BoxScore):
        result = format_box_score(sample_box_score)
        assert "3-4" in result  # ftm-fta

    def test_totals_row_present(self, sample_box_score: BoxScore):
        result = format_box_score(sample_box_score)
        assert "TOTALS" in result

    def test_game_id_in_box_score(self, sample_box_score: BoxScore):
        result = format_box_score(sample_box_score)
        assert "[Game ID: 401234567]" in result


# ── format_player_stats ──────────────────────────────────────


class TestFormatPlayerStats:
    def test_has_mpg_column(self):
        players = [
            PlayerStats(
                name="Player One",
                position="G",
                games_played=25,
                minutes_per_game=30.5,
                ppg=15.2,
                rpg=4.1,
                apg=3.0,
                spg=1.5,
                bpg=0.3,
                topg=2.1,
                fg_pct=45.0,
                three_pct=38.0,
                ft_pct=82.0,
            )
        ]
        result = format_player_stats(players)
        assert "MPG" in result
        assert "30.5" in result

    def test_has_spg_bpg_topg_columns(self):
        players = [
            PlayerStats(
                name="Player Two",
                position="F",
                games_played=20,
                spg=2.0,
                bpg=1.5,
                topg=1.8,
            )
        ]
        result = format_player_stats(players)
        assert "SPG" in result
        assert "BPG" in result
        assert "TOPG" in result

    def test_has_ft_pct_column(self):
        players = [
            PlayerStats(
                name="Player Three",
                position="C",
                games_played=15,
                ft_pct=75.5,
            )
        ]
        result = format_player_stats(players)
        assert "FT%" in result
        assert "75.5" in result

    def test_empty_list(self):
        result = format_player_stats([])
        assert "No player stats available" in result


# ── format_game_detail ────────────────────────────────────────


class TestFormatGameDetail:
    def test_shows_venue(self, sample_game: Game):
        result = format_game_detail(sample_game)
        assert "Rupp Arena" in result

    def test_shows_broadcast(self, sample_game: Game):
        result = format_game_detail(sample_game)
        assert "Broadcast: ESPN" in result

    def test_shows_records(self, sample_game: Game):
        result = format_game_detail(sample_game)
        assert "20-3" in result
        assert "18-5" in result

    def test_shows_half_scores(self, sample_game: Game):
        result = format_game_detail(sample_game)
        assert "1st" in result
        assert "2nd" in result

    def test_shows_conference_game_flag(self, sample_game: Game):
        result = format_game_detail(sample_game)
        assert "Conference Game" in result

    def test_shows_game_id(self, sample_game: Game):
        result = format_game_detail(sample_game)
        assert "[Game ID: 401234567]" in result

    def test_live_game_shows_period_clock(self):
        game = Game(
            id="401888888",
            status="in",
            status_detail="2nd Half 5:30",
            period=2,
            clock="5:30",
            home=TeamScore(team_name="Duke", score=40),
            away=TeamScore(team_name="UNC", score=38),
        )
        result = format_game_detail(game)
        assert "Period: 2" in result
        assert "Clock: 5:30" in result


# ── format_team_stats ─────────────────────────────────────────


class TestFormatTeamStats:
    def test_shows_games_played(self):
        stats = TeamStats(team_name="Florida", games_played=25, ppg=80.0)
        result = format_team_stats(stats)
        assert "Games Played: 25" in result

    def test_no_games_played_when_zero(self):
        stats = TeamStats(team_name="Florida", games_played=0)
        result = format_team_stats(stats)
        assert "Games Played" not in result

    def test_shows_off_def_rpg(self):
        stats = TeamStats(
            team_name="Florida",
            rpg=35.0,
            offensive_rpg=10.0,
            defensive_rpg=25.0,
        )
        result = format_team_stats(stats)
        assert "Off: 10.0" in result
        assert "Def: 25.0" in result

    def test_no_off_def_rpg_when_zero(self):
        stats = TeamStats(team_name="Florida", rpg=35.0)
        result = format_team_stats(stats)
        assert "Off:" not in result
        assert "Def:" not in result


# ── format_comparison ─────────────────────────────────────────


class TestFormatComparison:
    def test_shows_off_def_rpg_when_available(self):
        team1 = TeamStats(
            team_name="Florida",
            offensive_rpg=10.0,
            defensive_rpg=25.0,
        )
        team2 = TeamStats(
            team_name="Kentucky",
            offensive_rpg=11.0,
            defensive_rpg=24.0,
        )
        comp = TeamComparison(
            team1=team1,
            team2=team2,
            advantages={
                "Offensive Rebounds Per Game": "Kentucky",
                "Defensive Rebounds Per Game": "Florida",
            },
        )
        result = format_comparison(comp)
        assert "Off RPG" in result
        assert "Def RPG" in result

    def test_no_off_def_rpg_when_zero(self):
        team1 = TeamStats(team_name="Florida")
        team2 = TeamStats(team_name="Kentucky")
        comp = TeamComparison(team1=team1, team2=team2, advantages={})
        result = format_comparison(comp)
        assert "Off RPG" not in result
        assert "Def RPG" not in result
