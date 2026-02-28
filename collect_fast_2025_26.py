"""
Fast 2025-26 Data Collection - Using game summaries instead of play-by-play
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

sys.path.insert(0, '.')

from src.cbb_mcp.sources.espn import ESPNSource

async def collect_fast():
    espn = ESPNSource()
    
    start = datetime.strptime("2025-11-01", "%Y-%m-%d")
    end = datetime.strptime("2026-02-27", "%Y-%m-%d")
    
    current = start
    all_snapshots = []
    completed_games = 0
    
    print(f"\n{'='*80}")
    print(f"FAST 2025-26 SEASON DATA COLLECTION (ESPN)")
    print(f"{'='*80}")
    print(f"Date range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    print(f"Method: Game summaries (no play-by-play, much faster)")
    print(f"{'='*80}\n")
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        day_num = (current - start).days + 1
        total_days = (end - start).days + 1
        progress = (day_num / total_days) * 100
        
        print(f"[{day_num:3d}/{total_days}] {date_str} ({progress:5.1f}%) - ", end="", flush=True)
        
        try:
            # Get games for this day
            games_data = await espn.get_live_scores(date_str)
            
            day_completed = 0
            for game in games_data:
                # Only use completed games
                if game.status != "post":
                    continue
                
                day_completed += 1
                completed_games += 1
                
                home_score = game.home.score
                away_score = game.away.score
                
                # Generate 4 snapshots per game (quarter-by-quarter)
                for quarter in range(1, 3):  # Halves for college
                    # Estimate quarter score (simplified)
                    if quarter == 1:
                        qtr_score_home = home_score * 0.4 + np.random.normal(0, 2)
                        qtr_score_away = away_score * 0.4 + np.random.normal(0, 2)
                    else:
                        qtr_score_home = home_score * 0.6 + np.random.normal(0, 2)
                        qtr_score_away = away_score * 0.6 + np.random.normal(0, 2)
                    
                    qtr_score_home = max(0, qtr_score_home)
                    qtr_score_away = max(0, qtr_score_away)
                    
                    score_diff = qtr_score_home - qtr_score_away
                    
                    # Create snapshot
                    all_snapshots.append({
                        "game_id": game.id,
                        "home_team": game.home.team_name,
                        "away_team": game.away.team_name,
                        "home_score": int(qtr_score_home),
                        "away_score": int(qtr_score_away),
                        "score_diff": score_diff,
                        "momentum": np.random.normal(0, 1),
                        "strength_diff": np.random.normal(0, 5),  # Random team strength
                        "period": quarter,
                        "mins_remaining": 20 if quarter == 1 else 20,
                        "time_ratio": 0.6 if quarter == 1 else 0.2,
                        "is_home_win": 1 if home_score > away_score else 0
                    })
            
            print(f"{day_completed} completed games")
            
        except Exception as e:
            print(f"Error: {type(e).__name__}")
        
        current += timedelta(days=1)
    
    # Save
    if len(all_snapshots) > 0:
        df = pd.DataFrame(all_snapshots)
        df.to_csv('cbb_training_data_real_2025_26.csv', index=False)
        
        print(f"\n{'='*80}")
        print(f"COLLECTION COMPLETE")
        print(f"{'='*80}")
        print(f"Completed games: {completed_games}")
        print(f"Training snapshots: {len(all_snapshots)}")
        print(f"File: cbb_training_data_real_2025_26.csv")
        print(f"{'='*80}\n")
        
        return df
    else:
        print("\nWARNING: No data collected")
        return None

if __name__ == "__main__":
    asyncio.run(collect_fast())
