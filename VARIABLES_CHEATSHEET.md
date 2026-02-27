# ML Training Variables — Quick Cheatsheet

## The 4 Input Features

These are the ONLY variables the model sees:

```
┌─────────────────────────────────────────────────────────────┐
│           LIVE GAME STATE (INPUT TO MODEL)                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  score_diff = Home Score - Away Score                        │
│  Example: 48 - 42 = +6                                       │
│  Range: -30 to +30 typically                                 │
│                                                              │
│  time_ratio = Minutes Remaining / 40 Minutes                 │
│  Example: 5 mins left / 40 total = 0.125                     │
│  Range: 0.0 (game over) to 1.0+ (overtime)                   │
│                                                              │
│  mins_remaining = Minutes Left in Current Period             │
│  Example: 5 minutes in 2nd half                              │
│  Range: 0-20 (resets each period)                            │
│                                                              │
│  period = Which Half/Overtime                                │
│  Example: 2 (second half)                                    │
│  Range: 1 (1st half), 2 (2nd half), 3+ (OT)                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
        ↓
   [BOTH MODELS PROCESS THESE 4 VARIABLES]
        ↓
┌─────────────────────────────────────────────────────────────┐
│              PREDICTED OUTPUT (PROBABILITY)                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  is_home_win (LABEL) = Did home team win?                    │
│  Values: 0 (loss) or 1 (win)                                 │
│  Example: 1 (yes, home team won)                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Training Data Dimensions

```
Training CSV (cbb_training_data.csv)
├─ Rows: 1,000 to 100,000+ (each = one game moment)
└─ Columns: 10
   ├─ game_id (string)        — Unique game ID
   ├─ home_team (string)      — Home team name
   ├─ away_team (string)      — Away team name
   ├─ home_score (int)        — Home team score at that moment
   ├─ away_score (int)        — Away team score at that moment
   ├─ score_diff (int)        — FEATURE: home - away
   ├─ period (int)            — FEATURE: 1 or 2
   ├─ mins_remaining (int)    — FEATURE: 0-20
   ├─ time_ratio (float)      — FEATURE: mins_remaining / 40
   └─ is_home_win (int)       — LABEL: 0 or 1 ← What we're training to predict
```

---

## Train/Test Split

```
10,000 total snapshots
    ├─ 80% TRAINING SET (8,000 snapshots)
    │  └─ Used to train both LR and XGB models
    │
    └─ 20% TEST SET (2,000 snapshots)
       └─ Used to evaluate accuracy WITHOUT cheating
```

---

## Model 1: Logistic Regression (LR)

```
INPUT: X_train_scaled (scaled features)
  ├─ Scaled means: (value - mean) / standard_deviation
  ├─ Why? LR is sensitive to feature scale
  ├─ Example:
  │  Original: score_diff = 5
  │  Scaled: (5 - avg_diff) / std_diff = 0.2
  │
OUTPUT: lr_probs (probability for each snapshot)
  ├─ Range: 0.0 (definitely away win) to 1.0 (definitely home win)
  ├─ Example: [0.23, 0.67, 0.45, 0.89, ...]
  │
EVALUATION:
  ├─ lr_acc = Accuracy (e.g., 64%)
  └─ lr_brier = Brier Score (e.g., 0.18)
```

---

## Model 2: XGBoost (XGB)

```
INPUT: X_train (raw features, NO scaling)
  ├─ XGB can handle raw values directly
  ├─ XGB builds decision trees to find patterns
  ├─ Example: "IF score_diff > 5 AND time_ratio < 0.2 THEN home likely loses"
  │
PARAMETERS:
  ├─ n_estimators=100    → Build 100 decision trees
  ├─ max_depth=4         → Each tree can be 4 levels deep
  ├─ learning_rate=0.1   → Each tree contributes 10% of weight
  │
OUTPUT: xgb_probs (probability for each snapshot)
  ├─ Range: 0.0 to 1.0
  ├─ Example: [0.31, 0.72, 0.49, 0.91, ...]
  │
EVALUATION:
  ├─ xgb_acc = Accuracy (e.g., 67%)
  └─ xgb_brier = Brier Score (e.g., 0.16)
```

---

## Ensemble: Combining Both Models

```
Step 1: Get both predictions for the same test set
  ├─ lr_probs = [0.23, 0.67, 0.45, 0.89, ...]
  └─ xgb_probs = [0.31, 0.72, 0.49, 0.91, ...]

Step 2: Simple average
  ├─ ensemble_probs = (lr_probs + xgb_probs) / 2
  ├─ Example first prediction: (0.23 + 0.31) / 2 = 0.27
  └─ Result: [0.27, 0.695, 0.47, 0.90, ...]

Step 3: Evaluate combined model
  ├─ ensemble_acc = 67.89%
  └─ ensemble_brier = 0.1598
```

---

## What Gets Saved (Bundle)

```
cbb_predictor_bundle.joblib
├─ lr_model (sklearn LogisticRegression object)
│  └─ Contains: weights, intercept, ready to predict
├─ xgb_model (xgboost XGBClassifier object)
│  └─ Contains: 100 decision trees, parameters
├─ scaler (sklearn StandardScaler object)
│  └─ Contains: mean and std of training features
├─ features (list of strings)
│  └─ ['score_diff', 'time_ratio', 'mins_remaining', 'period']
└─ weights (dict)
   └─ {'lr': 0.5, 'xgb': 0.5}  ← How to combine predictions
```

---

## Live Prediction Flow

```
Real Game Right Now
├─ Home: 45, Away: 42, Time: 2:30 left in 2nd half
│
├─ Extract features:
│  ├─ score_diff = 45 - 42 = 3
│  ├─ time_ratio = 2.5 / 40 = 0.0625
│  ├─ mins_remaining = 2.5
│  └─ period = 2
│
├─ Load bundle: {lr_model, xgb_model, scaler}
│
├─ LR prediction:
│  ├─ Scale features
│  ├─ Run through LR model
│  └─ Get: 0.58 (58% home win)
│
├─ XGB prediction:
│  ├─ Use raw features
│  ├─ Run through 100 decision trees
│  └─ Get: 0.62 (62% home win)
│
└─ Ensemble result:
   └─ (0.58 + 0.62) / 2 = 0.60 = 60% HOME WIN PROBABILITY
```

---

## Metric Meanings

### Accuracy
```
How many predictions are correct?

Example: 1,340 out of 2,000 test predictions correct
Accuracy = 1,340 / 2,000 = 0.67 = 67%

Good: 60%+
Bad: 50% (same as coin flip!)
```

### Brier Score
```
Average squared error of probabilities

If we predict 0.8 (80%) but actual is 1.0 (won), error = (0.8-1.0)² = 0.04
If we predict 0.2 (20%) but actual is 0.0 (lost), error = (0.2-0.0)² = 0.04
Average across all predictions = Brier Score

Good: < 0.20
Bad: 0.25+
Range: 0.0 (perfect) to 1.0 (terrible)
```

---

## Example: Full Training Session Output

```
$ python dashboard/scripts/collect_historical_data.py \
    --start 2024-11-01 --end 2025-03-01 --output training.csv

Processing date: 2024-11-01
  Fetching PBP for game: Xavier @ Duke
  Snapshot created: Xavier leading by 2, 15 mins left, 2nd half
  ...more snapshots...
Processing date: 2024-11-02
  ...
Done! Total snapshots collected: 8,547
Data saved to training.csv


$ python dashboard/scripts/train_predictor.py --input training.csv

Loading data from training.csv...
Training Logistic Regression (Anchor Model)...
  LR Accuracy: 64.23%, Brier Score: 0.1823
Training XGBoost (Nuance Model)...
  XGB Accuracy: 67.45%, Brier Score: 0.1641
Consolidated Accuracy: 67.89%, Brier Score: 0.1598
Predictor bundle saved to cbb_predictor_bundle.joblib
```

---

## Variable Types Summary

| Variable | Type | Range | Example |
|----------|------|-------|---------|
| `game_id` | string | any | "401547812" |
| `home_team` | string | team name | "Duke" |
| `away_team` | string | team name | "UNC" |
| `home_score` | int | 0-150 | 45 |
| `away_score` | int | 0-150 | 42 |
| `score_diff` | int | -100 to +100 | 3 |
| `period` | int | 1, 2, 3+ | 2 |
| `mins_remaining` | float | 0.0 to 20.0 | 5.5 |
| `time_ratio` | float | 0.0 to 1.5+ | 0.1375 |
| `is_home_win` | int | 0 or 1 | 1 |
| `lr_probs` | float (array) | 0.0 to 1.0 | [0.23, 0.67, ...] |
| `xgb_probs` | float (array) | 0.0 to 1.0 | [0.31, 0.72, ...] |
| `ensemble_probs` | float (array) | 0.0 to 1.0 | [0.27, 0.695, ...] |
| `accuracy` | float | 0.0 to 1.0 | 0.6789 |
| `brier_score` | float | 0.0 to 1.0 | 0.1598 |

---

## Quick Commands

```bash
# 1. Collect data (one week of games)
python dashboard/scripts/collect_historical_data.py \
  --start 2025-02-01 --end 2025-02-08 \
  --output training.csv

# 2. Check how much data you have
wc -l training.csv  # Should be > 500 rows

# 3. View first few rows
head -5 training.csv

# 4. Train the model
python dashboard/scripts/train_predictor.py --input training.csv

# 5. Check if bundle was created
ls -lh cbb_predictor_bundle.joblib

# 6. Use the model in your app (automatic on startup)
python dashboard/app.py
```

---

## Debugging

| Problem | Check |
|---------|-------|
| "Not enough data" | Is your CSV < 100 rows? Collect more days. |
| Accuracy 50% | Model isn't learning. Need more/better data. |
| Brier score 0.35+ | Predictions are too uncertain. |
| Train time > 5 min | Try `n_estimators=50` instead of 100. |
| Predict time > 1 sec | Model is too complex; reduce `max_depth`. |

