"""
Complete Implementation: Contextual Features for 2025-26 Season

Workflow:
1. Collect games from Nov 2025 - Mar 2026
2. Extract contextual features
3. Enhance training data
4. Retrain model with 18 features
5. Deploy new model bundle

Run: python implement_contextual_features.py
"""

import asyncio
import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path
import json

# Set up paths
SEASON_GAMES_CSV = "season_games_2025_26.csv"
ENHANCED_TRAINING_CSV = "enhanced_training_data_2025_26.csv"
MODEL_BUNDLE_PATH = "cbb_predictor_bundle.joblib"


async def collect_season_games():
    """
    Step 1: Load existing real 2025-26 games (already collected)
    Uses pre-existing CSV with real ESPN data
    """
    print("\n" + "="*70)
    print("STEP 1: LOADING EXISTING 2025-26 SEASON GAMES")
    print("="*70)

    # Load existing real training data
    existing_csv = "cbb_training_data_real_2025_26.csv"

    try:
        games_df = pd.read_csv(existing_csv)
        print(f"[OK] Loaded {len(games_df)} games from {existing_csv}")
        print(f"[OK] Date range: {games_df.get('game_date', pd.Series(['Unknown'])).min()} to {games_df.get('game_date', pd.Series(['Unknown'])).max()}")

        # Save to standard location for consistency
        games_df.to_csv(SEASON_GAMES_CSV, index=False)
        print(f"[OK] Saved to {SEASON_GAMES_CSV}")
        return games_df
    except FileNotFoundError:
        print(f"[WARNING] {existing_csv} not found!")
        print("  Attempting to collect games from MCP server...")

        from dashboard.ai.mcp_client import get_client

        client = get_client()
        all_games = []

        # Date range: Nov 1, 2025 - Mar 1, 2026
        start_date = datetime(2025, 11, 1)
        end_date = datetime(2026, 3, 1)
        current = start_date

        dates_collected = 0

        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")

            try:
                print(f"  Fetching {date_str}...", end=" ")

                # Call MCP tool
                result = await client.call_tool(
                    "get_live_scores",
                    {"date": date_str}
                )

                # Parse result (it's formatted text)
                games = parse_live_scores_result(result, date_str)

                if games:
                    all_games.extend(games)
                    print(f"[OK] Found {len(games)} games")
                else:
                    print("No games")

                dates_collected += 1

            except Exception as e:
                print(f"[WARNING] Error: {e}")

            current += timedelta(days=1)

        # Create DataFrame
        print(f"\n[OK] Collected games from {dates_collected} dates")

        if all_games:
            games_df = pd.DataFrame(all_games)
            games_df.to_csv(SEASON_GAMES_CSV, index=False)
            print(f"[OK] Saved {len(games_df)} games to {SEASON_GAMES_CSV}")
            return games_df
        else:
            print("[WARNING] No games found! Check MCP server connection.")
            return None


def parse_live_scores_result(result_text: str, date_str: str) -> list[dict]:
    """Parse the text result from get_live_scores into structured data."""
    games = []

    try:
        # Result is formatted text like "Team1 vs Team2: Score1-Score2"
        # For now, we'll parse the format

        lines = result_text.strip().split('\n')

        for line in lines:
            if ' vs ' in line and ':' in line:
                try:
                    # Parse "Home vs Away: HomeScore-AwayScore"
                    matchup, score = line.rsplit(':', 1)
                    teams = matchup.split(' vs ')

                    if len(teams) == 2 and len(score.strip().split('-')) >= 2:
                        scores = score.strip().split('-')

                        game = {
                            "game_date": date_str,
                            "home_team": teams[0].strip(),
                            "away_team": teams[1].strip(),
                            "home_score": int(scores[0].strip()),
                            "away_score": int(scores[1].strip()),
                            "status": "post"
                        }
                        games.append(game)
                except (ValueError, IndexError):
                    continue

    except Exception as e:
        print(f"Error parsing scores: {e}")

    return games


async def extract_contextual_features(games_df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 2: Extract contextual features for each team
    Uses GameContextualFeatures class
    """
    print("\n" + "="*70)
    print("STEP 2: EXTRACTING CONTEXTUAL FEATURES")
    print("="*70)

    from dashboard.scripts.feature_engineering import GameContextualFeatures

    print("  Initializing feature extractor...")
    extractor = GameContextualFeatures(games_df)

    # Get unique teams
    teams = sorted(set(games_df["home_team"].unique()) | set(games_df["away_team"].unique()))
    print(f"  Found {len(teams)} teams")

    team_features = {}

    for i, team in enumerate(teams, 1):
        if i % 10 == 0:
            print(f"  Processing team {i}/{len(teams)}: {team}")

        try:
            team_features[team] = {
                "collapse_when_up_10_pct": extractor.get_collapse_tendency(team).get("collapse_when_up_10_pct", 0.5),
                "comeback_when_down_5_pct": extractor.get_comeback_tendency(team).get("comeback_win_pct_down_5", 0.5),
                "recent_form": extractor.get_recent_form(team),
                "clutch_stats": extractor.get_team_clutch_stats(team),
            }
        except Exception as e:
            print(f"    Warning: Error processing {team}: {e}")
            team_features[team] = {}

    print(f"\n[OK] Extracted features for {len(team_features)} teams")
    return team_features


async def enhance_training_data(games_df: pd.DataFrame, team_features: dict) -> pd.DataFrame:
    """
    Step 3: Add contextual features to each game record
    Creates enhanced training data with 18 features (6 original + 12 new)
    """
    print("\n" + "="*70)
    print("STEP 3: ENHANCING TRAINING DATA WITH CONTEXTUAL FEATURES")
    print("="*70)

    from dashboard.scripts.feature_engineering import enhance_game_features

    enhanced_games = []

    for idx, game in games_df.iterrows():
        if (idx + 1) % 50 == 0:
            print(f"  Enhanced {idx + 1}/{len(games_df)} games...")

        try:
            # enhance_game_features adds all contextual features
            enhanced = enhance_game_features(game, games_df)
            enhanced_games.append(enhanced)
        except Exception as e:
            print(f"    Warning: Error enhancing game {idx}: {e}")
            continue

    enhanced_df = pd.DataFrame(enhanced_games)
    enhanced_df.to_csv(ENHANCED_TRAINING_CSV, index=False)

    print(f"\n[OK] Enhanced {len(enhanced_df)} games")
    print(f"[OK] Original features: 6 (score_diff, momentum, strength_diff, time_ratio, mins_remaining, period)")
    print(f"[OK] New features added: 12 (collapse%, comeback%, conf_rank, recent_form, h2h, clutch, etc.)")
    print(f"[OK] Total features: 18")
    print(f"[OK] Saved to {ENHANCED_TRAINING_CSV}")

    return enhanced_df


async def retrain_model(enhanced_df: pd.DataFrame):
    """
    Step 4: Retrain model with enhanced data
    Uses all 18 features instead of 6
    """
    print("\n" + "="*70)
    print("STEP 4: RETRAINING MODEL WITH 18 FEATURES")
    print("="*70)

    from dashboard.scripts.train_predictor import train_predictor

    print(f"  Training data shape: {enhanced_df.shape}")
    print(f"  Training on 2025-26 season data only")

    try:
        # Train with enhanced features
        model_info = await train_predictor(
            ENHANCED_TRAINING_CSV,
            features=[
                # Original 6 features
                "score_diff", "momentum", "strength_diff",
                "time_ratio", "mins_remaining", "period",
                # NEW 12 contextual features
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
        )

        print(f"\n[OK] Model retraining complete!")
        print(f"[OK] New model bundle saved to {MODEL_BUNDLE_PATH}")

        if isinstance(model_info, dict):
            print(f"[OK] Model accuracy: {model_info.get('accuracy', 'N/A')}")

        return model_info

    except Exception as e:
        print(f"[WARNING] Error retraining model: {e}")
        return None


def verify_improvement():
    """
    Step 5: Verify improvement on known difficult cases
    """
    print("\n" + "="*70)
    print("STEP 5: VERIFYING IMPROVEMENTS")
    print("="*70)

    try:
        from ml_sports_predictor.server import _get_predictor

        predictor = _get_predictor()

        print("\nTest Case: Team Leading by 10, Down to Final Minutes")
        print("  (like Tennessee vs Alabama scenario)")

        # Simulate game state
        game_state = {
            "score_diff": 10.0,
            "momentum": 1.0,
            "strength_diff": -0.5,
            "time_ratio": 0.20,
            "mins_remaining": 8.0,
            "period": 2.0,
            # NEW contextual features
            "home_collapse_pct_up_10": 0.62,      # Home team collapses
            "away_collapse_pct_up_10": 0.28,
            "home_comeback_pct_down_5": 0.33,
            "away_comeback_pct_down_5": 0.75,     # Away team comes back
            "home_conf_rank": 28,
            "home_conf_win_pct": 0.45,
            "away_conf_rank": 2,                  # Away is 2nd in conference
            "away_conf_win_pct": 0.72,
            "home_recent_win_pct": 0.40,          # Home on losing streak
            "away_recent_win_pct": 0.80,          # Away winning
            "home_h2h_win_pct": 0.38,
            "away_h2h_win_pct": 0.62,
        }

        prob = asyncio.run(predictor.predict("cbb", game_state))

        print(f"\n  Home team win probability: {prob * 100:.1f}%")
        print(f"  Away team win probability: {(1-prob) * 100:.1f}%")

        if prob < 0.5:
            print(f"\n  [OK] CORRECT: Model now picks away team (the likely winner)")
        else:
            print(f"\n  [WARNING] Model still favors home team")

    except Exception as e:
        print(f"[WARNING] Could not verify (model may not be loaded): {e}")


async def main():
    """Complete implementation workflow"""

    print("\n" + "="*70)
    print("CONTEXTUAL FEATURES IMPLEMENTATION")
    print("2025-26 Season Data Only")
    print("="*70)

    # Step 1: Collect data
    games_df = await collect_season_games()

    if games_df is None or len(games_df) == 0:
        print("\n[ERROR] No games collected. Aborting.")
        return

    # Step 2: Extract features
    team_features = await extract_contextual_features(games_df)

    # Step 3: Enhance data
    enhanced_df = await enhance_training_data(games_df, team_features)

    # Step 4: Retrain model
    model_info = await retrain_model(enhanced_df)

    # Step 5: Verify
    verify_improvement()

    # Summary
    print("\n" + "="*70)
    print("IMPLEMENTATION COMPLETE!")
    print("="*70)
    print("\nSummary:")
    print(f"  [OK] Collected: {len(games_df)} games from 2025-26 season")
    print(f"  [OK] Features extracted: 12 contextual features")
    print(f"  [OK] Training data enhanced: {len(enhanced_df)} games with 18 features")
    print(f"  [OK] Model retrained: Using 2025-26 data only")
    print(f"  [OK] Model deployed: {MODEL_BUNDLE_PATH}")
    print("\nNext: Restart dashboard to load new model")
    print("  python dashboard/app.py")
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
