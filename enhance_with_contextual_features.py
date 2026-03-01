"""
Enhance 2025-26 Training Data with Contextual Features

This script takes the existing real 2025-26 training data and adds
12 contextual features to create an 18-feature training set for
improved model accuracy.

Features added:
- home_collapse_pct_up_10, away_collapse_pct_up_10
- home_comeback_pct_down_5, away_comeback_pct_down_5
- home_conf_rank, home_conf_win_pct, away_conf_rank, away_conf_win_pct
- home_recent_win_pct, away_recent_win_pct
- home_h2h_win_pct, away_h2h_win_pct
"""

import pandas as pd
import numpy as np
from collections import defaultdict
from pathlib import Path

# File paths
INPUT_CSV = "cbb_training_data_real_2025_26.csv"
OUTPUT_CSV = "enhanced_training_data_2025_26.csv"
MODEL_BUNDLE_PATH = "cbb_predictor_bundle.joblib"

def compute_contextual_features(df: pd.DataFrame) -> dict:
    """
    Compute contextual features for each team from the training data.

    Returns:
        Dict mapping team_name -> {feature_key: value}
    """
    print("\n" + "="*70)
    print("COMPUTING CONTEXTUAL FEATURES FOR ALL TEAMS")
    print("="*70)

    team_features = {}

    # Get unique teams
    teams = set(df["home_team"].unique()) | set(df["away_team"].unique())
    print(f"Found {len(teams)} unique teams")

    for i, team in enumerate(sorted(teams), 1):
        if i % 10 == 0:
            print(f"  Processing {i}/{len(teams)}: {team}")

        # Get all games for this team (home and away)
        home_games = df[df["home_team"] == team].copy()
        away_games = df[df["away_team"] == team].copy()

        # For away games, flip the perspective
        away_games_flipped = away_games.copy()
        away_games_flipped = away_games_flipped.rename(columns={
            "home_team": "away_team",
            "away_team": "home_team",
            "home_score": "away_score",
            "away_score": "home_score"
        })
        away_games_flipped["is_home_win"] = 1 - away_games_flipped["is_home_win"]
        away_games_flipped["score_diff"] = -away_games_flipped["score_diff"]

        # Combine all games from this team's perspective
        all_games = pd.concat([home_games, away_games_flipped], ignore_index=True)

        if len(all_games) == 0:
            team_features[team] = {
                "collapse_pct_up_10": 0.5,
                "comeback_pct_down_5": 0.5,
                "conf_rank": 50,
                "conf_win_pct": 0.5,
                "recent_win_pct": 0.5,
                "h2h_records": {},
                "clutch_win_pct": 0.5,
            }
            continue

        # Collapse: When up 10+ at some point, did team lose?
        # We use score_diff as proxy. If score_diff >= 10 at any point and team didn't win -> collapse
        up_10_games = all_games[all_games["score_diff"] >= 10]
        if len(up_10_games) > 0:
            collapse_pct = 1 - up_10_games["is_home_win"].mean()
        else:
            collapse_pct = 0.5

        # Comeback: When down 5+ at some point, did team win?
        # If score_diff <= -5 (we're down 5+) and we won -> comeback
        down_5_games = all_games[all_games["score_diff"] <= -5]
        if len(down_5_games) > 0:
            comeback_pct = down_5_games["is_home_win"].mean()
        else:
            comeback_pct = 0.5

        # Overall win rate (proxy for recent form)
        recent_win_pct = all_games["is_home_win"].mean()

        # Clutch: Games where score_diff was close (within 5) -> did team win?
        close_games = all_games[abs(all_games["score_diff"]) <= 5]
        if len(close_games) > 0:
            clutch_win_pct = close_games["is_home_win"].mean()
        else:
            clutch_win_pct = 0.5

        team_features[team] = {
            "collapse_pct_up_10": collapse_pct,
            "comeback_pct_down_5": comeback_pct,
            "conf_rank": 50,  # Placeholder, would need ESPN standings
            "conf_win_pct": recent_win_pct,  # Use overall win rate as proxy
            "recent_win_pct": recent_win_pct,
            "h2h_records": {},
            "clutch_win_pct": clutch_win_pct,
        }

    print(f"[OK] Computed features for {len(team_features)} teams")
    return team_features


def compute_h2h_records(df: pd.DataFrame, teams: list) -> dict:
    """
    Compute head-to-head records for all team pairs.

    Returns:
        Dict mapping (team1, team2) -> team1_win_pct
    """
    print("\n" + "="*70)
    print("COMPUTING HEAD-TO-HEAD RECORDS")
    print("="*70)

    h2h = {}

    for team1 in teams:
        for team2 in teams:
            if team1 == team2:
                continue

            # Get games between these teams
            matchups = df[
                ((df["home_team"] == team1) & (df["away_team"] == team2)) |
                ((df["home_team"] == team2) & (df["away_team"] == team1))
            ]

            if len(matchups) == 0:
                h2h[(team1, team2)] = 0.5
                continue

            # Count team1 wins
            team1_wins = 0
            for _, game in matchups.iterrows():
                if game["home_team"] == team1:
                    if game["is_home_win"] == 1:
                        team1_wins += 1
                else:  # team1 is away
                    if game["is_home_win"] == 0:
                        team1_wins += 1

            h2h[(team1, team2)] = team1_wins / len(matchups) if len(matchups) > 0 else 0.5

    print(f"[OK] Computed H2H records for {len(h2h)} team pairs")
    return h2h


def enhance_dataframe(df: pd.DataFrame, team_features: dict, h2h: dict) -> pd.DataFrame:
    """
    Add contextual features to each row in the dataframe.
    """
    print("\n" + "="*70)
    print("ENHANCING TRAINING DATA WITH CONTEXTUAL FEATURES")
    print("="*70)

    # Add new columns with zeros first
    new_columns = [
        "home_collapse_pct_up_10",
        "away_collapse_pct_up_10",
        "home_comeback_pct_down_5",
        "away_comeback_pct_down_5",
        "home_conf_rank",
        "home_conf_win_pct",
        "away_conf_rank",
        "away_conf_win_pct",
        "home_recent_win_pct",
        "away_recent_win_pct",
        "home_h2h_win_pct",
        "away_h2h_win_pct",
    ]

    for col in new_columns:
        df[col] = 0.0

    # Populate features for each row
    for idx, row in df.iterrows():
        if (idx + 1) % 500 == 0:
            print(f"  Enhanced {idx + 1}/{len(df)} games...")

        home_team = row["home_team"]
        away_team = row["away_team"]

        # Get features for home team
        home_feats = team_features.get(home_team, {})
        df.loc[idx, "home_collapse_pct_up_10"] = home_feats.get("collapse_pct_up_10", 0.5)
        df.loc[idx, "home_comeback_pct_down_5"] = home_feats.get("comeback_pct_down_5", 0.5)
        df.loc[idx, "home_conf_rank"] = home_feats.get("conf_rank", 50)
        df.loc[idx, "home_conf_win_pct"] = home_feats.get("conf_win_pct", 0.5)
        df.loc[idx, "home_recent_win_pct"] = home_feats.get("recent_win_pct", 0.5)
        df.loc[idx, "home_h2h_win_pct"] = h2h.get((home_team, away_team), 0.5)

        # Get features for away team
        away_feats = team_features.get(away_team, {})
        df.loc[idx, "away_collapse_pct_up_10"] = away_feats.get("collapse_pct_up_10", 0.5)
        df.loc[idx, "away_comeback_pct_down_5"] = away_feats.get("comeback_pct_down_5", 0.5)
        df.loc[idx, "away_conf_rank"] = away_feats.get("conf_rank", 50)
        df.loc[idx, "away_conf_win_pct"] = away_feats.get("conf_win_pct", 0.5)
        df.loc[idx, "away_recent_win_pct"] = away_feats.get("recent_win_pct", 0.5)
        df.loc[idx, "away_h2h_win_pct"] = h2h.get((away_team, home_team), 0.5)

    print(f"[OK] Enhanced {len(df)} games")
    return df


def main():
    print("\n" + "="*70)
    print("ENHANCING CBB TRAINING DATA WITH CONTEXTUAL FEATURES")
    print("2025-26 Season Data Only")
    print("="*70)

    # Load training data
    print(f"\nLoading {INPUT_CSV}...")
    df = pd.read_csv(INPUT_CSV)
    print(f"[OK] Loaded {len(df)} training snapshots from {len(df)//2} unique games")

    # Compute features
    teams = list(set(df["home_team"].unique()) | set(df["away_team"].unique()))
    team_features = compute_contextual_features(df)
    h2h = compute_h2h_records(df, teams)

    # Enhance dataframe
    df_enhanced = enhance_dataframe(df, team_features, h2h)

    # Save enhanced data
    df_enhanced.to_csv(OUTPUT_CSV, index=False)
    print(f"\n[OK] Saved enhanced training data to {OUTPUT_CSV}")

    # Show summary
    print("\n" + "="*70)
    print("FEATURE ENGINEERING SUMMARY")
    print("="*70)
    print(f"Original features: 6 (game_id, score_diff, momentum, strength_diff, period, mins_remaining, time_ratio, is_home_win)")
    print(f"New contextual features: 12 (collapse_pct, comeback_pct, conf_rank, conf_win_pct, recent_win_pct, h2h_win_pct)")
    print(f"Total features: 18")
    print(f"\nEnhanced data shape: {df_enhanced.shape}")
    print(f"Ready for model retraining!")
    print("\n" + "="*70)

    # Next steps
    print("\nNEXT STEPS:")
    print("1. Run model retraining with enhanced features:")
    print("   python dashboard/scripts/train_predictor.py --input enhanced_training_data_2025_26.csv")
    print("\n2. Restart dashboard:")
    print("   python dashboard/app.py")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
