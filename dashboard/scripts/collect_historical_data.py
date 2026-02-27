"""
Predictive Engine — Historical Data Collector.
Usage: python dashboard/scripts/collect_historical_data.py --start 2024-11-01 --end 2025-03-01 --output training_data.csv

This script fetches play-by-play data for past games and formats it into 
snapshots (one per minute or significant event) for ML training.
"""

import argparse
import asyncio
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import structlog
from collections import deque

# Ensure project root is on path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from src.cbb_mcp.sources.cbbpy_source import CbbpySource
from src.cbb_mcp.sources.espn import ESPNSource

logger = structlog.get_logger()

async def get_team_strength_map(espn_source):
    """Fetch season stats for all teams to build a strength proxy."""
    print("Building team strength map (PPG Differential)...")
    # This is a simplification; ideally we'd have historical stats for the exact date.
    # Here we use current season stats as a proxy for team quality.
    try:
        # We need a list of team IDs. Let's search for a broad set or just rely on IDs we encounter.
        # For this script, we'll fetch stats on-demand and cache them in memory.
        return {}
    except Exception as e:
        print(f"Error building strength map: {e}")
        return {}

async def collect_data(start_date: str, end_date: str, output_file: str):
    cbbpy = CbbpySource()
    espn = ESPNSource()
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    current = start
    all_snapshots = []
    strength_cache = {} # team_id -> ppg_diff
    
    print(f"Starting data collection from {start_date} to {end_date}...")

    async def get_strength(team_id):
        if team_id in strength_cache:
            return strength_cache[team_id]
        try:
            stats = await espn.get_team_stats(team_id)
            diff = stats.ppg - stats.opp_ppg
            strength_cache[team_id] = diff
            return diff
        except:
            return 0.0

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        print(f"Processing date: {date_str}")
        
        try:
            # Fetch games for this day
            games = await cbbpy.get_live_scores(date_str)
            
            for game in games:
                if game.status != "post": # Only train on completed games
                    continue
                
                print(f"  Fetching PBP for game: {game.away.team_name} @ {game.home.team_name} ({game.id})")
                try:
                    pbp = await cbbpy.get_play_by_play(game.id)
                    
                    if not pbp or not pbp.plays:
                        continue
                        
                    # Determine winner
                    final_home = game.home.score
                    final_away = game.away.score
                    home_win = 1 if final_home > final_away else 0
                    
                    # Fetch team strengths (context)
                    # Note: game.home.team_id might be missing from cbbpy, we might need a mapping
                    # For now, if ID is missing, we use 0.0 strength
                    home_strength = await get_strength(game.home.team_id) if game.home.team_id else 0.0
                    away_strength = await get_strength(game.away.team_id) if game.away.team_id else 0.0
                    strength_diff = home_strength - away_strength
                    
                    # Create snapshots from PBP
                    last_minute_sampled = -1
                    score_history = deque(maxlen=5) # To calculate momentum (last 4-5 mins)
                    
                    for play in pbp.plays:
                        clock = play.clock or "20:00"
                        try:
                            parts = clock.split(":")
                            mins = int(parts[0]) if len(parts) > 0 else 0
                            period = play.period # 1 or 2
                            total_mins_remaining = mins if period == 2 else mins + 20
                        except:
                            continue
                            
                        # Momentum calculation: Change in score_diff over the last few samples
                        current_diff = play.score_home - play.score_away
                        
                        # Sample roughly every minute
                        if total_mins_remaining != last_minute_sampled:
                            # Calculate momentum if we have history
                            momentum = 0.0
                            if len(score_history) > 0:
                                momentum = current_diff - score_history[0] # Change since the oldest sample in window
                            
                            all_snapshots.append({
                                "game_id": game.id,
                                "home_team": game.home.team_name,
                                "away_team": game.away.team_name,
                                "home_score": play.score_home,
                                "away_score": play.score_away,
                                "score_diff": current_diff,
                                "momentum": momentum,
                                "strength_diff": strength_diff,
                                "period": period,
                                "mins_remaining": total_mins_remaining,
                                "time_ratio": total_mins_remaining / 40.0,
                                "is_home_win": home_win
                            })
                            last_minute_sampled = total_mins_remaining
                            score_history.append(current_diff)
                            
                except Exception as e:
                    print(f"    Error fetching PBP for {game.id}: {e}")
                    
        except Exception as e:
            print(f"Error fetching games for {date_str}: {e}")
            
        current += timedelta(days=1)
        if len(all_snapshots) > 1000:
            df = pd.DataFrame(all_snapshots)
            df.to_csv(output_file, index=False)
            print(f"Intermediate save: {len(all_snapshots)} snapshots collected.")

    df = pd.DataFrame(all_snapshots)
    df.to_csv(output_file, index=False)
    print(f"Done! Total snapshots collected: {len(all_snapshots)}")
    print(f"Data saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2025-02-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2025-02-15", help="End date YYYY-MM-DD")
    parser.add_argument("--output", default="cbb_training_data.csv", help="Output CSV path")
    args = parser.parse_args()
    
    asyncio.run(collect_data(args.start, args.end, args.output))
