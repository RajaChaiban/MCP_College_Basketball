# Game Time Tracking — Win Probability Graph Guide

## Overview

The win probability graph now displays **game time** instead of clock time, making it easy to track how probability changes as the game progresses from start to finish.

---

## What is Game Time?

Game time shows the **quarter and remaining time** in that quarter:

```
Q1 18:30  ← 1st Quarter, 18:30 remaining
Q1 10:00  ← 1st Quarter, 10:00 remaining
Q2 18:30  ← 2nd Quarter, 18:30 remaining (after halftime)
Q2 05:15  ← 2nd Quarter, 5:15 remaining
Q2 00:00  ← End of regulation (or overtime starts)
OT1 05:00 ← 1st Overtime, 5:00 remaining
OT2 03:00 ← 2nd Overtime, 3:00 remaining
```

---

## Why Game Time is Better

### Before (Clock Time)
```
X-axis: 14:30:45, 14:31:12, 14:31:47, 14:32:15
Problem: No connection to actual game progress
Result: Can't tell where in the game things happened
```

### After (Game Time)
```
X-axis: Q1 18:30, Q1 15:00, Q2 18:30, Q2 05:15
Benefit: Exactly shows game progression
Result: Easy to see momentum throughout game
```

---

## Reading the Graph

### Time Format

**Regular Game:**
```
Q1 = 1st Quarter (first 20 minutes)
Q2 = 2nd Quarter (second 20 minutes)
```

**Overtime:**
```
OT1 = 1st Overtime (5-minute period)
OT2 = 2nd Overtime (5-minute period)
OT3+ = Additional overtimes
```

**Time Remaining:**
```
MM:SS = Minutes:Seconds remaining in quarter
18:30 = 18 minutes 30 seconds left
00:00 = Quarter ended (or last second of game)
```

---

## Example: Complete Game Flow

### Duke vs UNC Game

```
Q1 Progression (1st Quarter):
──────────────────────────────────
Q1 18:30  │ 52% │ Game starts balanced
Q1 18:00  │ 53% │ Slight Duke advantage
Q1 15:00  │ 58% │ Duke scores 2x
Q1 10:00  │ 62% │ Duke building lead
Q1 05:00  │ 65% │ Duke on scoring run
Q1 00:00  │ 68% │ Quarter ends, Duke +12


Q2 Progression (2nd Quarter):
──────────────────────────────────
Q2 18:30  │ 70% │ Halftime break, Duke lead holds
Q2 15:00  │ 68% │ UNC scores, cuts lead
Q2 12:00  │ 65% │ UNC gaining momentum
Q2 10:00  │ 60% │ Game tightening up
Q2 08:00  │ 55% │ Line crossing! Very close
Q2 06:00  │ 58% │ Duke responds with basket
Q2 03:00  │ 62% │ Duke re-takes lead
Q2 00:00  │ 62% │ Duke wins by 3


On the Graph:
├─ X-axis: Q1 → Q2 progression
├─ Q1 line: Steady upward (Duke taking control)
├─ Crossing at Q2 08:00: Most exciting moment!
├─ Q2 line: Down then up (momentum swing)
└─ Final: Duke's line flat at 62% (confident win)
```

---

## Key Insights from Game Time Graphs

### Quarter-by-Quarter Analysis

**Look for these patterns:**

1. **Q1 Analysis**
   - Does team build early lead?
   - Is it a close first quarter?
   - Who gets momentum?

2. **Q2 Analysis**
   - Does halftime momentum change things?
   - Do they extend lead or blow it?
   - Any comebacks starting?

3. **Momentum Shifts**
   - Lines crossing = game getting competitive
   - Steep slopes = quick momentum changes
   - Flat lines = team very confident

4. **Closing Time**
   - Last 5 minutes (Q2 05:00 - Q2 00:00)
   - Usually most dramatic swings
   - Where upsets happen

---

## Visual Examples

### Example 1: Dominant Win

```
Graph shows:
  Leading team line: Steady upward
  Trailing team line: Steady downward

Duke vs Wake Forest:

Q1 18:30  │ Duke 55%  │ Duke favored
Q1 10:00  │ Duke 65%  │ Duke extending
Q2 18:30  │ Duke 70%  │ Halftime lead
Q2 10:00  │ Duke 78%  │ Pulling away
Q2 05:00  │ Duke 85%  │ Game decided
Q2 00:00  │ Duke 95%  │ Duke wins big

Graph pattern: Lines separate widely
Meaning: Blowout game
```

### Example 2: Close Game

```
Graph shows:
  Both lines hover near 50%
  Many crossings
  Lots of momentum swings

Duke vs UNC:

Q1 18:30  │ Duke 52%  │ Balanced start
Q1 10:00  │ Duke 58%  │ Duke slight lead
Q2 18:30  │ Duke 55%  │ Still close
Q2 15:00  │ UNC 52%   │ Line crosses!
Q2 10:00  │ Duke 54%  │ Back and forth
Q2 05:00  │ UNC 51%   │ Very competitive
Q2 02:00  │ Duke 53%  │ Late lead change
Q2 00:00  │ Duke 55%  │ Close win

Graph pattern: Lines crisscross, stay near 50%
Meaning: Competitive game
```

### Example 3: Comeback

```
Graph shows:
  One line rising as other falls
  Lines cross in dramatic moment
  Winner takes over late

UNC vs Duke (UNC wins):

Q1 18:30  │ Duke 58%  │ Duke favored
Q1 10:00  │ Duke 65%  │ Duke pulling away
Q2 18:30  │ Duke 68%  │ Halftime: Duke +15
Q2 15:00  │ Duke 65%  │ UNC starts scoring
Q2 10:00  │ Duke 55%  │ Momentum shifting
Q2 08:00  │ UNC 52%   │ Lines cross! Comeback!
Q2 05:00  │ UNC 60%   │ UNC takes over
Q2 02:00  │ UNC 75%   │ UNC pulls ahead
Q2 00:00  │ UNC 80%   │ UNC wins

Graph pattern: Line swap (X-shape)
Meaning: Dramatic comeback
```

---

## How the System Works

### Data Collection

**Every 30 seconds during live games:**

1. Get current game state:
   ```
   period: 2 (Q2)
   clock: "05:15" (5:15 remaining)
   home_score: 45
   away_score: 42
   ```

2. Format as game time:
   ```
   game_time = "Q2 05:15"
   ```

3. Calculate win probability:
   ```
   probability = ensemble_model(score_diff, time_ratio, mins_remaining, period)
   ```

4. Store in history:
   ```
   {"time": "Q2 05:15", "prob": 0.62}
   ```

5. Display on graph:
   ```
   X-axis: Q2 05:15
   Y-axis: 62%
   ```

### Real-Time Updates

```
Live Game In Progress:

Time            Action
────────────────────────────────────
Q2 08:15 00s    Fetch new score
Q2 08:15 01s    Calculate probability
Q2 08:15 02s    Add to history
Q2 08:15 03s    Update graph (NEW POINT ADDED)

Q2 07:45 00s    Fetch new score
Q2 07:45 01s    Calculate probability
Q2 07:45 02s    Add to history
Q2 07:45 03s    Update graph (ANOTHER POINT)

(Pattern repeats every 30 seconds)
```

---

## Practical Analysis Tips

### Analyzing a Game

1. **Look at Q1**
   - See initial prob from oddsmakers
   - Early momentum building?
   - Any surprise runs?

2. **Check Q2 Start**
   - Did halftime adjustments help?
   - Is trend continuing?
   - Any momentum reversals?

3. **Focus on Closing Time**
   - Last 5 minutes most interesting
   - Where upsets happen
   - Watch line angles (steep = fast change)

4. **Note Line Crossings**
   - Mark when lines cross (game tied in prob)
   - Usually exciting moment
   - Momentum swing happening

5. **Compare to Expectations**
   - Does early favorite hold on?
   - Does underdog make it close?
   - Are there surprises?

---

## Customization

### Want to Change Time Format?

Edit `dashboard/callbacks/map_callbacks.py`:

```python
def _format_game_time(game) -> str:
    period = getattr(game, "period", 1) or 1
    clock = getattr(game, "clock", "20:00") or "20:00"

    # Modify this section to change format:
    if period <= 2:
        quarter = f"Q{period}"
    else:
        quarter = f"OT{period - 2}"

    return f"{quarter} {clock}"

    # Examples of other formats:
    # return f"P{period} {clock}"          # P1, P2, etc.
    # return f"Period {period}: {clock}"   # Period 1: 18:30
    # return f"{clock} (Q{period})"        # 18:30 (Q1)
```

Do the same in `dashboard/callbacks/game_callbacks.py`.

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Time shows "??:??" | Game object missing period/clock | Check game data is loaded |
| Graph X-axis not sorted | Old data still in history | Restart app to clear cache |
| Time doesn't update | Graph not refreshing | Check live-refresh interval (30s) |
| Q2 time doesn't reset | Clock showing minutes wrong | Verify ESPN clock format |

---

## Summary

✅ **Game time shows quarter and remaining time**
✅ **Easy to track probability throughout game**
✅ **See momentum shifts clearly**
✅ **Understand game flow better**
✅ **Compare quarters and periods**
✅ **Identify critical moments**

The graph now tells a complete story of how the game progresses and who controls the momentum! 🏀
