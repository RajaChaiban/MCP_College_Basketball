# Model Validation Report: Miami (OH) vs Western Michigan

**Date**: 2026-02-27
**Issue**: Model gave insufficient confidence to 21-0 Miami (OH) vs Western Michigan

---

## Summary

The model predicted **68.1% for Miami (OH) to win**, which is mathematically correct given the data, but **too conservative for an undefeated team**. The root cause is **synthetic training data**, not the model architecture.

---

## Root Cause Analysis

### Problem 1: Synthetic Training Data (PRIMARY ISSUE)
- **What happened**: We created 800-row training set by duplicating and varying 2024-25 season data
- **Why it matters**: Model learned patterns from FAKE data, not real 2025-26 games
- **Impact on Miami-WM prediction**:
  - Model never saw a 21-0 team in training data
  - Model never learned "undefeated teams have higher win probability"
  - Model only knows "strength_diff=13.2 → 68% confidence"

### Problem 2: Missing Features for Pre-Game
- **Features used**: [score_diff, momentum, strength_diff, time_ratio, mins_remaining, period]
- **For pre-game**: score_diff=0, momentum=0, other features are defaults
- **Result**: Model relies ENTIRELY on `strength_diff` (PPG differential)
- **Why it's insufficient**:
  - An undefeated 21-0 team should matter more than PPG
  - Team rankings are better predictors than PPG alone
  - Win-loss records carry important information

### Problem 3: Data Quality Issue
- **ESPN data returns**: `opponent_ppg = 0.0` for all teams
- **Current workaround**: Can't calculate true PPG differential
- **Impact**: Strength calculations are unreliable

---

## How to Verify the Model is Weak

### Test 1: Vegas Lines
```
Compare model predictions to actual betting lines.

For undefeated teams (21-0):
  - Vegas should give >75% implied probability
  - Our model gives 55-68% depending on PPG

Action: Get Vegas lines, compare to model predictions
```

### Test 2: Simple Record Check
```python
# If Miami is 21-0 and WM has losses:
# Model should MINIMUM give Miami:
# 75-80% for pre-game (before considering rankings)

# Currently gives: 68.1% (too low)
```

### Test 3: Backtest Against Real Outcomes
```
1. Take all 2025-26 games completed so far
2. Get model predictions for each game
3. Calculate accuracy, calibration (do 70% predictions = 70% win rate?)
4. Compare to betting lines
5. If calibration is poor, synthetic data is the culprit
```

---

## Root Cause Summary

| Issue | Evidence | Impact |
|-------|----------|--------|
| **Synthetic Training Data** | 800 rows = replicated 2024-25 | Model learned fake patterns |
| **No Record Features** | Features don't include W-L record | Can't recognize undefeated teams |
| **PPG-Only Pre-Game** | Feature engineering missing for pre-game | Underfits strong favorites |
| **Broken Data Source** | ESPN opp_ppg = 0.0 always | Strength calculation unreliable |

---

## How to Fix (Recommended Roadmap)

### Phase 1: SHORT TERM (1-2 days)
**Collect Real 2025-26 Data**

```bash
# Use the updated collection script
python dashboard/scripts/collect_historical_data.py \
  --start 2025-11-01 \
  --end 2026-02-27 \
  --output cbb_training_data_real_2025_26.csv

# Wait for collection to complete (may take hours)
```

**Retrain with Real Data**
```bash
python dashboard/scripts/train_predictor.py \
  --input cbb_training_data_real_2025_26.csv
```

---

### Phase 2: MEDIUM TERM (3-5 days)
**Improve Feature Engineering**

1. **Pre-game features**:
   - Add `ranking_diff` (home rank - away rank)
   - Add `record_pct` (wins / total games)
   - Add `home_court_factor` (+3 pp)
   - **Remove** reliance on score_diff for pre-game (it's always 0)

2. **Fix Data Sources**:
   - Get opponent PPG from CBS or another source
   - Calculate true defensive efficiency
   - Add SOS (strength of schedule)

3. **Feature Engineering Code** (in `dashboard/ai/predictor.py`):
```python
def get_pregame_features(home_team, away_team):
    # Current: only strength_diff
    # New: ranking_diff + record_pct + home_court

    ranking_diff = home_team.ranking - away_team.ranking
    record_pct_home = home_team.wins / home_team.games
    record_pct_away = away_team.wins / away_team.games
    home_court = 0.03  # +3 percentage points

    return {
        'ranking_diff': ranking_diff,
        'record_diff': record_pct_home - record_pct_away,
        'strength_diff': home_team.ppg_diff - away_team.ppg_diff,
        'home_court': home_court,
        # ... in-game features when game starts
    }
```

---

### Phase 3: LONG TERM (1-2 weeks)
**Separate Pre-Game and In-Game Models**

```
Pre-Game Model:
  - Input: Ranking diff, record diff, home court, strength diff
  - Target: Team quality before any points scored
  - Calibrate against Vegas lines

In-Game Model:
  - Input: Score diff, momentum, time remaining, strength diff, period
  - Target: Win probability during game (changes minute-by-minute)
  - Should be very accurate (70%+ on score diff alone)
```

---

## Validation Checklist

Before declaring the model "fixed", verify:

- [ ] **Accuracy Test**: Run on all 2025-26 games to date, check accuracy >65%
- [ ] **Calibration Test**: Do 70% predictions actually win 70% of the time?
- [ ] **Vegas Alignment**: Compare to betting lines, should correlate >0.8
- [ ] **Known Cases**:
  - [ ] Undefeated team should have >75% pre-game win prob
  - [ ] Home court should add 3-5 percentage points
  - [ ] Ranking diff should matter more than PPG alone
- [ ] **Backtest**: Test on 2024-25 season data (should beat random baseline by >10%)

---

## Current Model Status

**Status**: SYNTHETIC DATA MODE (not recommended for production)

| Metric | Value | Status |
|--------|-------|--------|
| Training Data | 800 rows (synthetic) | POOR - not real 2025-26 |
| Accuracy | 75% on training set | GOOD - but on fake data |
| Calibration | Brier 0.165 | GOOD - but on fake data |
| Pre-Game Prediction | Miami 68% | QUESTIONABLE - too low for 21-0 |
| Data Source Quality | PPG only, broken opp_ppg | POOR |
| Feature Coverage | 6 features | POOR - missing team context |

---

## Next Steps

**Immediate** (today):
- [ ] Get real 2025-26 game data (full or partial)
- [ ] Retrain model with real outcomes
- [ ] Test on Miami-WM game and similar misses

**This week**:
- [ ] Add ranking and record features
- [ ] Fix data source for opponent stats
- [ ] Validate calibration

**This month**:
- [ ] Separate pre-game and in-game models
- [ ] Calibrate against Vegas lines
- [ ] Full backtest suite

---

## Questions to Answer

1. **Did real game happen?** What was actual outcome of Miami (OH) vs WM?
2. **What was Vegas line?** Compare model 68% to Vegas implied probability
3. **Other 21-0 teams?** How did model perform on other undefeated matchups?
4. **Ranking data available?** Can we get AP/Coaches poll rankings per team?
5. **Why stop at synthetic data?** Can we get any real 2025-26 game data quickly?

---

**Report Generated**: 2026-02-27
**Conclusion**: Model is functional but trained on fake data. Needs real 2025-26 season data and better pre-game features before production use.
