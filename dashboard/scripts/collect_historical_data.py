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

# Ensure project root is on path
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from src.cbb_mcp.sources.cbbpy_source import CbbpySource

logger = structlog.get_logger()

async def collect_data(start_date: str, end_date: str, output_file: str):
    source = CbbpySource()
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    current = start
    all_snapshots = []
    
    print(f"Starting data collection from {start_date} to {end_date}...")

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        print(f"Processing date: {date_str}")
        
        try:
            # Fetch games for this day
            games = await source.get_live_scores(date_str)
            
            for game in games:
                if game.status != "post": # Only train on completed games
                    continue
                
                print(f"  Fetching PBP for game: {game.away.team_name} @ {game.home.team_name} ({game.id})")
                try:
                    pbp = await source.get_play_by_play(game.id)
                    
                    if not pbp or not pbp.plays:
                        continue
                        
                    # Determine winner
                    final_home = game.home.score
                    final_away = game.away.score
                    home_win = 1 if final_home > final_away else 0
                    
                    # Create snapshots from PBP
                    # We'll take a snapshot every 2 minutes of game time to avoid over-sampling
                    last_minute_sampled = -1
                    
                    for play in pbp.plays:
                        # Simple clock parsing (MM:SS)
                        clock = play.clock or "20:00"
                        try:
                            parts = clock.split(":")
                            mins = int(parts[0]) if len(parts) > 0 else 0
                            # Total game seconds remaining (assuming 2 halves of 20 mins)
                            # This is a simplification for H1/H2
                            period = play.period # 1 or 2
                            total_mins_remaining = mins if period == 2 else mins + 20
                        except:
                            continue
                            
                        # Sample roughly every minute
                        if total_mins_remaining != last_minute_sampled:
                            all_snapshots.append({
                                "game_id": game.id,
                                "home_team": game.home.team_name,
                                "away_team": game.away.team_name,
                                "home_score": play.score_home,
                                "away_score": play.score_away,
                                "score_diff": play.score_home - play.score_away,
                                "period": period,
                                "mins_remaining": total_mins_remaining,
                                "time_ratio": total_mins_remaining / 40.0, # Feature: time progress
                                "is_home_win": home_win # Label
                            })
                            last_minute_sampled = total_mins_remaining
                            
                except Exception as e:
                    print(f"    Error fetching PBP for {game.id}: {e}")
                    
        except Exception as e:
            print(f"Error fetching games for {date_str}: {e}")
            
        current += timedelta(days=1)
        # Periodic save
        if len(all_snapshots) > 1000:
            df = pd.DataFrame(all_snapshots)
            df.to_csv(output_file, index=False)
            print(f"Intermediate save: {len(all_snapshots)} snapshots collected.")

    # Final save
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
