"""
Feature Engineering for Enhanced ML Predictor

Adds contextual features that capture:
- Clutch performance (last 5 minutes)
- Performance by score margin (e.g., collapse when up 10)
- Conference strength and ranking
- Recent team form (streaks, momentum)
- Head-to-head history

These features should be added to training data to prevent scenarios like:
- Tennessee losing when up 10 (model needs to learn this tendency)
- Alabama winning from down positions (clutch performance)
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional


class GameContextualFeatures:
    """Extract contextual features from game history."""

    def __init__(self, games_df: pd.DataFrame):
        """
        Initialize with historical games data.

        Args:
            games_df: DataFrame with columns:
                - game_date
                - home_team, away_team
                - home_score, away_score
                - home_rank, away_rank
                - home_conf, away_conf
                - status (pre/live/post)
        """
        self.games_df = games_df.sort_values("game_date")

    def get_team_clutch_stats(
        self, team: str, days_back: int = 365, position: str = "home"
    ) -> dict:
        """
        Get clutch performance (last 5 minutes) for a team.

        Args:
            team: Team name
            days_back: Days of history to analyze
            position: "home", "away", or "any"

        Returns:
            Dict with clutch_wins, clutch_losses, clutch_win_pct
        """
        cutoff = datetime.now() - timedelta(days=days_back)
        recent = self.games_df[self.games_df["game_date"] > cutoff]

        if position == "home":
            team_games = recent[recent["home_team"] == team]
        elif position == "away":
            team_games = recent[recent["away_team"] == team]
        else:
            home_games = recent[recent["home_team"] == team]
            away_games = recent[recent["away_team"] == team]
            team_games = pd.concat([home_games, away_games])

        # Count close games won/lost (clutch scenarios)
        clutch_games = team_games[
            (team_games["status"] == "post")
            & (abs(team_games["score_diff"].abs()) <= 5)
        ]

        clutch_wins = len(
            clutch_games[
                (clutch_games["home_team"] == team)
                & (clutch_games["home_score"] > clutch_games["away_score"])
                | ((clutch_games["away_team"] == team)
                   & (clutch_games["away_score"] > clutch_games["home_score"]))
            ]
        )
        clutch_losses = len(clutch_games) - clutch_wins

        return {
            "clutch_wins": clutch_wins,
            "clutch_losses": clutch_losses,
            "clutch_win_pct": clutch_wins / max(1, len(clutch_games)),
            "clutch_games_count": len(clutch_games),
        }

    def get_collapse_tendency(self, team: str, days_back: int = 365) -> dict:
        """
        Analyze team's tendency to lose when ahead by specific margins.

        Returns dict like:
        {
            "lose_when_up_10": 8,  # lost 8 games after being up 10+
            "win_when_up_10": 5,
            "collapse_pct": 0.62,
        }
        """
        cutoff = datetime.now() - timedelta(days=days_back)
        recent = self.games_df[self.games_df["game_date"] > cutoff]

        # Find games where team was ahead at some point (estimate from final margin)
        home_games = recent[recent["home_team"] == team]
        away_games = recent[recent["away_team"] == team]

        results = {
            "up_10_plus": {"wins": 0, "losses": 0},
            "up_5_to_10": {"wins": 0, "losses": 0},
            "up_2_to_5": {"wins": 0, "losses": 0},
        }

        for _, game in home_games.iterrows():
            margin = game["home_score"] - game["away_score"]
            if margin >= 10:
                results["up_10_plus"]["wins"] += 1
            elif margin < 0:  # Lost (was likely up at some point)
                results["up_10_plus"]["losses"] += 1

        for _, game in away_games.iterrows():
            margin = game["away_score"] - game["home_score"]
            if margin >= 10:
                results["up_10_plus"]["wins"] += 1
            elif margin < 0:  # Lost (was likely up at some point)
                results["up_10_plus"]["losses"] += 1

        total_up_10 = (
            results["up_10_plus"]["wins"] + results["up_10_plus"]["losses"]
        )
        collapse_pct = (
            results["up_10_plus"]["losses"] / total_up_10 if total_up_10 > 0 else 0.5
        )

        return {
            "up_10_plus_record": results["up_10_plus"],
            "collapse_when_up_10_pct": collapse_pct,
            "total_up_10_games": total_up_10,
        }

    def get_comeback_tendency(self, team: str, days_back: int = 365) -> dict:
        """
        Analyze team's ability to win from down positions.

        Returns dict like:
        {
            "comeback_wins_down_5": 12,
            "comeback_losses_down_5": 3,
            "comeback_pct_down_5": 0.80,
        }
        """
        cutoff = datetime.now() - timedelta(days=days_back)
        recent = self.games_df[self.games_df["game_date"] > cutoff]

        home_games = recent[recent["home_team"] == team]
        away_games = recent[recent["away_team"] == team]

        results = {
            "down_5_or_more": {"wins": 0, "losses": 0},
            "down_2_to_5": {"wins": 0, "losses": 0},
            "down_1": {"wins": 0, "losses": 0},
        }

        for _, game in home_games.iterrows():
            final_margin = game["away_score"] - game["home_score"]
            if final_margin >= 5 and game["home_score"] > game["away_score"]:
                results["down_5_or_more"]["wins"] += 1
            elif final_margin >= 5:
                results["down_5_or_more"]["losses"] += 1

        for _, game in away_games.iterrows():
            final_margin = game["home_score"] - game["away_score"]
            if final_margin >= 5 and game["away_score"] > game["home_score"]:
                results["down_5_or_more"]["wins"] += 1
            elif final_margin >= 5:
                results["down_5_or_more"]["losses"] += 1

        total_comebacks = (
            results["down_5_or_more"]["wins"] + results["down_5_or_more"]["losses"]
        )
        comeback_pct = (
            results["down_5_or_more"]["wins"] / total_comebacks
            if total_comebacks > 0
            else 0.5
        )

        return {
            "down_5_plus_record": results["down_5_or_more"],
            "comeback_win_pct_down_5": comeback_pct,
            "total_down_5_games": total_comebacks,
        }

    def get_conference_strength(self, team: str, conf: str) -> dict:
        """Get team's strength relative to conference."""
        conf_games = self.games_df[
            (self.games_df["home_conf"] == conf) | (self.games_df["away_conf"] == conf)
        ]
        conf_games = conf_games[conf_games["status"] == "post"]

        team_games = conf_games[
            (conf_games["home_team"] == team) | (conf_games["away_team"] == team)
        ]

        wins = 0
        for _, game in team_games.iterrows():
            if game["home_team"] == team and game["home_score"] > game["away_score"]:
                wins += 1
            elif (game["away_team"] == team and
                  game["away_score"] > game["home_score"]):
                wins += 1

        conf_win_pct = wins / max(1, len(team_games))

        return {
            "conf_wins": wins,
            "conf_losses": len(team_games) - wins,
            "conf_win_pct": conf_win_pct,
            "conf_rank_estimate": self._estimate_conf_rank(conf, conf_games),
        }

    def get_recent_form(self, team: str, games_count: int = 5) -> dict:
        """Get team's recent form (last N games)."""
        recent = self.games_df[self.games_df["status"] == "post"].tail(
            games_count * 10
        )  # Look back enough

        team_games = recent[
            (recent["home_team"] == team) | (recent["away_team"] == team)
        ].tail(games_count)

        wins = 0
        for _, game in team_games.iterrows():
            if game["home_team"] == team and game["home_score"] > game["away_score"]:
                wins += 1
            elif (game["away_team"] == team and
                  game["away_score"] > game["home_score"]):
                wins += 1

        return {
            "recent_record": f"{wins}-{len(team_games) - wins}",
            "recent_win_pct": wins / max(1, len(team_games)),
            "on_losing_streak": wins < 2,
            "games_analyzed": len(team_games),
        }

    def get_head_to_head(self, team1: str, team2: str, games_limit: int = 10) -> dict:
        """Get head-to-head record between two teams."""
        h2h = self.games_df[
            (
                ((self.games_df["home_team"] == team1)
                 & (self.games_df["away_team"] == team2))
                | ((self.games_df["home_team"] == team2)
                   & (self.games_df["away_team"] == team1))
            )
            & (self.games_df["status"] == "post")
        ].tail(games_limit)

        team1_wins = 0
        for _, game in h2h.iterrows():
            if (game["home_team"] == team1 and
                game["home_score"] > game["away_score"]):
                team1_wins += 1
            elif (game["away_team"] == team1 and
                  game["away_score"] > game["home_score"]):
                team1_wins += 1

        return {
            "h2h_record": f"{team1_wins}-{len(h2h) - team1_wins}",
            "h2h_win_pct": team1_wins / max(1, len(h2h)),
            "games_vs_opponent": len(h2h),
        }

    @staticmethod
    def _estimate_conf_rank(conf: str, conf_games: pd.DataFrame) -> int:
        """Estimate conference rank from games."""
        # Simplified ranking based on conference win %
        return 1  # Placeholder


# ============================================================================
# Example: How to use these features to prevent Tennessee/Alabama scenario
# ============================================================================

def enhance_game_features(
    game: dict, teams_history: pd.DataFrame
) -> dict:
    """
    Enhance a game with contextual features.

    Args:
        game: Current game dict with home_team, away_team, home_score, away_score
        teams_history: Historical games DataFrame

    Returns:
        Enhanced game dict with additional contextual features
    """
    features = GameContextualFeatures(teams_history)

    enhanced = game.copy()

    # Add collapse tendency (Tennessee's tendency to lose when up 10)
    enhanced["home_collapse_pct"] = features.get_collapse_tendency(
        game["home_team"]
    )["collapse_when_up_10_pct"]
    enhanced["away_collapse_pct"] = features.get_collapse_tendency(
        game["away_team"]
    )["collapse_when_up_10_pct"]

    # Add comeback ability (Alabama's ability to win from down)
    enhanced["home_comeback_pct"] = features.get_comeback_tendency(
        game["home_team"]
    )["comeback_win_pct_down_5"]
    enhanced["away_comeback_pct"] = features.get_comeback_tendency(
        game["away_team"]
    )["comeback_win_pct_down_5"]

    # Add conference context
    enhanced["home_conf_info"] = features.get_conference_strength(
        game["home_team"], game.get("home_conf", "")
    )
    enhanced["away_conf_info"] = features.get_conference_strength(
        game["away_team"], game.get("away_conf", "")
    )

    # Add recent form
    enhanced["home_recent_form"] = features.get_recent_form(game["home_team"])
    enhanced["away_recent_form"] = features.get_recent_form(game["away_team"])

    # Add H2H
    enhanced["h2h"] = features.get_head_to_head(
        game["home_team"], game["away_team"]
    )

    return enhanced


if __name__ == "__main__":
    print("Feature Engineering Module")
    print("\nExample: Tennessee vs Alabama scenario")
    print("=" * 60)
    print("\nThese features would capture:")
    print("- Tennessee's collapse tendency when up 10+ (e.g., 62% lose rate)")
    print("- Alabama's comeback ability when down 5+ (e.g., 75% win rate)")
    print("- Alabama's 2nd in SEC ranking (conference strength)")
    print("- Tennessee on 2-3 losing streak (recent form)")
    print("\nWith these features added to the model:")
    print("→ Even if Tennessee up 10, model adjusts down due to collapse_pct")
    print("→ Even if Alabama down 5, model adjusts up due to comeback_pct")
    print("→ Conference context + recent form further tips odds toward Alabama")
