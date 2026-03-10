"""
Leakage-safe contextual feature construction for CBB training snapshots.

This module avoids the most direct leakage by using leave-one-game-out
aggregations for team and head-to-head context features.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import pandas as pd


def _safe_div(num: float, den: float, default: float = 0.5) -> float:
    return float(num) / float(den) if den > 0 else default


@dataclass
class TeamTotals:
    games: int = 0
    wins: int = 0


@dataclass
class PairTotals:
    games: int = 0
    wins: int = 0


@dataclass
class TeamEventTotals:
    up10_games: int = 0
    up10_losses: int = 0
    down5_games: int = 0
    down5_wins: int = 0


def add_contextual_features_leave_one_game_out(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 12 contextual features using leave-one-game-out statistics.

    Required columns:
    - game_id, home_team, away_team, is_home_win, score_diff
    """
    required = {"game_id", "home_team", "away_team", "is_home_win", "score_diff"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns for contextual features: {missing}")

    out = df.copy()

    # One canonical row per game for outcomes/team identities.
    games = (
        out.sort_values(["game_id"])
        .groupby("game_id", as_index=False)
        .agg(
            home_team=("home_team", "first"),
            away_team=("away_team", "first"),
            is_home_win=("is_home_win", "first"),
        )
    )

    # Team totals from game outcomes.
    team_totals: dict[str, TeamTotals] = defaultdict(TeamTotals)
    for row in games.itertuples(index=False):
        home = str(row.home_team)
        away = str(row.away_team)
        home_win = int(row.is_home_win)
        away_win = 1 - home_win
        team_totals[home].games += 1
        team_totals[home].wins += home_win
        team_totals[away].games += 1
        team_totals[away].wins += away_win

    # Ordered head-to-head totals: (team, opponent) -> totals from team perspective.
    pair_totals: dict[tuple[str, str], PairTotals] = defaultdict(PairTotals)
    for row in games.itertuples(index=False):
        home = str(row.home_team)
        away = str(row.away_team)
        home_win = int(row.is_home_win)
        away_win = 1 - home_win

        pair_totals[(home, away)].games += 1
        pair_totals[(home, away)].wins += home_win
        pair_totals[(away, home)].games += 1
        pair_totals[(away, home)].wins += away_win

    # Team event stats (collapse/comeback), built per team+game perspective.
    home_view = out[["game_id", "home_team", "score_diff", "is_home_win"]].rename(
        columns={"home_team": "team", "is_home_win": "team_win"}
    )
    away_view = out[["game_id", "away_team", "score_diff", "is_home_win"]].rename(
        columns={"away_team": "team", "is_home_win": "team_win"}
    )
    away_view["score_diff"] = -away_view["score_diff"]
    away_view["team_win"] = 1 - away_view["team_win"]
    team_view = pd.concat([home_view, away_view], ignore_index=True)

    team_game_events = (
        team_view.groupby(["team", "game_id"], as_index=False)
        .agg(
            ever_up10=("score_diff", lambda s: int((s >= 10).any())),
            ever_down5=("score_diff", lambda s: int((s <= -5).any())),
            team_win=("team_win", "first"),
        )
    )
    event_map: dict[tuple[str, Any], dict[str, int]] = {}
    team_event_totals: dict[str, TeamEventTotals] = defaultdict(TeamEventTotals)
    for row in team_game_events.itertuples(index=False):
        team = str(row.team)
        key = (team, row.game_id)
        team_win = int(row.team_win)
        ever_up10 = int(row.ever_up10)
        ever_down5 = int(row.ever_down5)
        event_map[key] = {
            "team_win": team_win,
            "ever_up10": ever_up10,
            "ever_down5": ever_down5,
        }

        if ever_up10:
            team_event_totals[team].up10_games += 1
            if team_win == 0:
                team_event_totals[team].up10_losses += 1
        if ever_down5:
            team_event_totals[team].down5_games += 1
            if team_win == 1:
                team_event_totals[team].down5_wins += 1

    def _team_win_pct_excluding_game(team: str, game_id: Any, team_win_current: int) -> float:
        totals = team_totals[team]
        return _safe_div(totals.wins - team_win_current, totals.games - 1, default=0.5)

    def _pair_pct_excluding_game(team: str, opp: str, team_win_current: int) -> float:
        pair = pair_totals[(team, opp)]
        return _safe_div(pair.wins - team_win_current, pair.games - 1, default=0.5)

    def _event_rates_excluding_game(team: str, game_id: Any) -> tuple[float, float]:
        totals = team_event_totals[team]
        ev = event_map.get((team, game_id), {"team_win": 0, "ever_up10": 0, "ever_down5": 0})
        ever_up10 = int(ev["ever_up10"])
        ever_down5 = int(ev["ever_down5"])
        team_win = int(ev["team_win"])

        up10_games = totals.up10_games - ever_up10
        up10_losses = totals.up10_losses - (1 if ever_up10 and team_win == 0 else 0)
        down5_games = totals.down5_games - ever_down5
        down5_wins = totals.down5_wins - (1 if ever_down5 and team_win == 1 else 0)

        collapse_pct = _safe_div(up10_losses, up10_games, default=0.5)
        comeback_pct = _safe_div(down5_wins, down5_games, default=0.5)
        return collapse_pct, comeback_pct

    def _rank_from_win_pct(win_pct: float) -> float:
        # Proxy rank [1..100], lower is better.
        return 1.0 + (1.0 - win_pct) * 99.0

    home_collapse: list[float] = []
    away_collapse: list[float] = []
    home_comeback: list[float] = []
    away_comeback: list[float] = []
    home_conf_rank: list[float] = []
    away_conf_rank: list[float] = []
    home_conf_win_pct: list[float] = []
    away_conf_win_pct: list[float] = []
    home_recent_win_pct: list[float] = []
    away_recent_win_pct: list[float] = []
    home_h2h_win_pct: list[float] = []
    away_h2h_win_pct: list[float] = []

    for row in out.itertuples(index=False):
        game_id = row.game_id
        home = str(row.home_team)
        away = str(row.away_team)
        home_win = int(row.is_home_win)
        away_win = 1 - home_win

        h_wp = _team_win_pct_excluding_game(home, game_id, home_win)
        a_wp = _team_win_pct_excluding_game(away, game_id, away_win)

        h_col, h_com = _event_rates_excluding_game(home, game_id)
        a_col, a_com = _event_rates_excluding_game(away, game_id)

        home_collapse.append(h_col)
        away_collapse.append(a_col)
        home_comeback.append(h_com)
        away_comeback.append(a_com)

        home_conf_rank.append(_rank_from_win_pct(h_wp))
        away_conf_rank.append(_rank_from_win_pct(a_wp))
        home_conf_win_pct.append(h_wp)
        away_conf_win_pct.append(a_wp)
        home_recent_win_pct.append(h_wp)
        away_recent_win_pct.append(a_wp)

        home_h2h_win_pct.append(_pair_pct_excluding_game(home, away, home_win))
        away_h2h_win_pct.append(_pair_pct_excluding_game(away, home, away_win))

    out["home_collapse_pct_up_10"] = home_collapse
    out["away_collapse_pct_up_10"] = away_collapse
    out["home_comeback_pct_down_5"] = home_comeback
    out["away_comeback_pct_down_5"] = away_comeback
    out["home_conf_rank"] = home_conf_rank
    out["home_conf_win_pct"] = home_conf_win_pct
    out["away_conf_rank"] = away_conf_rank
    out["away_conf_win_pct"] = away_conf_win_pct
    out["home_recent_win_pct"] = home_recent_win_pct
    out["away_recent_win_pct"] = away_recent_win_pct
    out["home_h2h_win_pct"] = home_h2h_win_pct
    out["away_h2h_win_pct"] = away_h2h_win_pct

    return out
