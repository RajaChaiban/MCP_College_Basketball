"""
Robust Real 2025-26 Data Collection with Progress Tracking
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
from collections import deque

sys.path.insert(0, '.')

from src.cbb_mcp.sources.cbbpy_source import CbbpySource

async def collect_real_data():
    cbbpy = CbbpySource()
    
    start = datetime.strptime("2025-11-01", "%Y-%m-%d")
    end = datetime.strptime("2026-02-27", "%Y-%m-%d")
    
    current = start
    all_snapshots = []
    total_games = 0
    completed_games = 0
    
    print(f"\n{'='*80}")
    print(f"REAL 2025-26 SEASON DATA COLLECTION")
    print(f"{'='*80}")
    print(f"Date range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    print(f"Output: cbb_training_data_real_2025_26.csv")
    print(f"{'='*80}\n")
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        day_num = (current - start).days + 1
        total_days = (end - start).days + 1
        progress = (day_num / total_days) * 100
        
        print(f"[{day_num:3d}/{total_days}] {date_str} ({progress:5.1f}%) - ", end="", flush=True)
        
        try:
            # Fetch games for this day
            games = await cbbpy.get_live_scores(date_str)
            
            day_snapshots = 0
            day_completed = 0
            
            for game in games:
                total_games += 1
                
                # Only train on completed games
                if game.status != "post":
                    continue
                
                day_completed += 1
                completed_games += 1
                
                try:
                    pbp = await cbbpy.get_play_by_play(game.id)
                    
                    if not pbp or not pbp.plays:
                        continue
                    
                    # Game outcome
                    final_home = game.home.score
                    final_away = game.away.score
                    home_win = 1 if final_home > final_away else 0
                    
                    # Simplified strength (using scores as proxy for team quality)
                    home_strength = final_home / max(final_away, 1)
                    away_strength = final_away / max(final_home, 1)
                    strength_diff = (home_strength - away_strength) * 10
                    
                    # Create snapshots from play-by-play
                    last_minute_sampled = -1
                    score_history = deque(maxlen=5)
                    
                    for play in pbp.plays:
                        clock = play.clock or "20:00"
                        try:
                            parts = clock.split(":")
                            mins = int(parts[0]) if len(parts) > 0 else 0
                            period = play.period or 1
                            total_mins_remaining = mins if period == 2 else mins + 20
                        except:
                            continue
                        
                        current_diff = play.score_home - play.score_away
                        
                        # Sample roughly every minute
                        if total_mins_remaining != last_minute_sampled:
                            momentum = 0.0
                            if len(score_history) > 0:
                                momentum = current_diff - score_history[0]
                            
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
                            day_snapshots += 1
                            last_minute_sampled = total_mins_remaining
                            score_history.append(current_diff)
                        
                except Exception as e:
                    pass  # Skip problematic games
            
            print(f"{day_completed} completed games, {day_snapshots} snapshots collected")
            
        except Exception as e:
            print(f"Error: {type(e).__name__}")
        
        current += timedelta(days=1)
    
    # Save
    df = pd.DataFrame(all_snapshots)
    df.to_csv('cbb_training_data_real_2025_26.csv', index=False)
    
    print(f"\n{'='*80}")
    print(f"COLLECTION COMPLETE")
    print(f"{'='*80}")
    print(f"Total games found: {total_games}")
    print(f"Completed games: {completed_games}")
    print(f"Training snapshots: {len(all_snapshots)}")
    print(f"File: cbb_training_data_real_2025_26.csv")
    print(f"{'='*80}\n")
    
    if len(all_snapshots) < 100:
        print("WARNING: Less than 100 snapshots collected. Data may be insufficient.")
    
    return df

if __name__ == "__main__":
    asyncio.run(collect_real_data())
