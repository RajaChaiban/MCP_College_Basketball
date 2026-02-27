# Predictive Engine — Complete Training Guide

## Overview

The predictive engine consists of **two scripts** that work together:

1. **`collect_historical_data.py`** — Fetches historical game data and creates training snapshots
2. **`train_predictor.py`** — Trains ML models and saves a reusable bundle

The result is `cbb_predictor_bundle.joblib` — a saved model file containing both trained models ready for live prediction.

---

## Step 1: Data Collection (`collect_historical_data.py`)

### What It Does
Fetches play-by-play data from completed games and converts it into training snapshots (one row = one moment in a game).

### Command
```bash
python dashboard/scripts/collect_historical_data.py \
  --start 2024-11-01 \
  --end 2025-03-01 \
  --output cbb_training_data.csv
```

### Variables Explained

#### **Input Arguments**
```python
--start "2024-11-01"      # Date to start collecting (YYYY-MM-DD)
--end "2025-03-01"        # Date to stop collecting
--output "cbb_training_data.csv"  # Where to save the training data
```

#### **Key Variables During Collection**

| Variable | Type | Meaning | Example |
|----------|------|---------|---------|
| `game_id` | string | Unique game identifier | "401547812" |
| `home_team` | string | Home team name | "Duke" |
| `away_team` | string | Away team name | "UNC" |
| `home_score` | int | Home team current score | 45 |
| `away_score` | int | Away team current score | 42 |
| `score_diff` | int | Score differential (home - away) | 3 |
| `period` | int | Game period (1=1st half, 2=2nd half) | 2 |
| `mins_remaining` | int | Minutes left in game (0-40) | 5 |
| `time_ratio` | float | Time progress ratio (0.0 to 1.0+) | 0.875 |
| `is_home_win` | int | **LABEL** — Did home team win? (0 or 1) | 1 |

### Data Flow

```
Historical Games
    ↓
For each game:
  - Get play-by-play events
  - For each minute of game:
    - Record: score, time, period, outcome
    - Store as one row in CSV
    ↓
Output: cbb_training_data.csv (thousands of rows)
```

### Example Output CSV

```
game_id,home_team,away_team,home_score,away_score,score_diff,period,mins_remaining,time_ratio,is_home_win
401547812,Duke,UNC,45,42,3,2,5,0.125,1
401547812,Duke,UNC,44,42,2,2,4,0.1,1
401547812,Duke,UNC,42,40,2,2,3,0.075,1
401547813,Kansas,Texas,60,58,2,2,1,0.025,1
401547814,Arizona,USC,55,58,-3,2,2,0.05,0
```

### Sampling Strategy

```python
# Sample every ~minute to avoid over-sampling
# This prevents training bias where late-game moments are overrepresented

# Example: If game has 2,400 seconds (40 minutes)
# We might get 40 snapshots instead of 2,400
# Each snapshot is one minute of game time
```

---

## Step 2: Model Training (`train_predictor.py`)

### What It Does
Takes the CSV from Step 1, trains two models (Logistic Regression + XGBoost), and saves them in a bundle.

### Command
```bash
python dashboard/scripts/train_predictor.py \
  --input cbb_training_data.csv
```

### Process Breakdown

#### **1. Load Data**
```python
df = pd.read_csv("cbb_training_data.csv")
# Result: DataFrame with thousands of rows
```

#### **2. Feature Selection**
```python
features = ['score_diff', 'time_ratio', 'mins_remaining', 'period']
X = df[features]           # Input features (what we use to predict)
y = df['is_home_win']      # Target label (what we're predicting)
```

**Why these 4 features?**
- `score_diff` — Current advantage/disadvantage in points
- `time_ratio` — How far into the game (0.0 = start, 1.0+ = end/OT)
- `mins_remaining` — Minutes left in current period
- `period` — Which half/OT (affects scoring patterns)

#### **3. Train-Test Split**
```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,        # 20% for testing, 80% for training
    random_state=42       # Reproducible split
)
```

**Example:**
- Total snapshots: 10,000
- Train set: 8,000 snapshots (to learn from)
- Test set: 2,000 snapshots (to evaluate performance)

---

## Model 1: Logistic Regression (Anchor Model)

### Why Logistic Regression?
- Provides **stable, calibrated probabilities** (0.0 to 1.0)
- Fast to train and predict
- Interpretable (we can see feature weights)
- Acts as a baseline

### Training Code
```python
# Step 1: Scale features (important for LR)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)  # Mean=0, StdDev=1
X_test_scaled = scaler.transform(X_test)

# Step 2: Train model
lr_model = LogisticRegression()
lr_model.fit(X_train_scaled, y_train)

# Step 3: Make predictions
lr_probs = lr_model.predict_proba(X_test_scaled)[:, 1]
# Result: Array of probabilities [0.23, 0.67, 0.45, ...]

# Step 4: Evaluate
lr_acc = accuracy_score(y_test, lr_model.predict(X_test_scaled))
# Example output: 0.64 (64% accuracy)

lr_brier = brier_score_loss(y_test, lr_probs)
# Example output: 0.18 (lower is better, range 0-1)
```

### Evaluation Metrics

| Metric | Meaning | Good Value |
|--------|---------|-----------|
| **Accuracy** | % correct predictions | 60%+ |
| **Brier Score** | Average squared error of probabilities | < 0.25 |

### Example Output
```
Logistic Regression Training:
  LR Accuracy: 64.23%, Brier Score: 0.1823
```

---

## Model 2: XGBoost (Nuance Model)

### Why XGBoost?
- Captures **non-linear patterns** (e.g., "close games are unpredictable")
- Builds ensemble of decision trees
- Often more accurate than LR on complex data

### Training Code
```python
# Create XGBoost model with specific parameters
xgb_model = XGBClassifier(
    n_estimators=100,        # 100 decision trees
    max_depth=4,             # Tree depth (deeper = more complex)
    learning_rate=0.1,       # How much each tree influences result
    random_state=42,         # Reproducible results
    use_label_encoder=False, # Don't use deprecated encoder
    eval_metric='logloss'    # Loss metric
)

# Train (note: XGB works on raw features, no scaling needed)
xgb_model.fit(X_train, y_train)

# Make predictions
xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
# Result: Array of probabilities [0.31, 0.72, 0.49, ...]

# Evaluate
xgb_acc = accuracy_score(y_test, xgb_model.predict(X_test))
xgb_brier = brier_score_loss(y_test, xgb_probs)
```

### XGBoost Parameters Explained

```python
n_estimators=100       # Number of trees to build
                       # Higher = more complex model, slower training
                       # But can improve accuracy (diminishing returns after 200)

max_depth=4            # How deep each tree can be
                       # 1-3 = shallow, underfitting risk
                       # 5-8 = moderate, good balance
                       # 10+ = deep, overfitting risk (memorizes data)

learning_rate=0.1      # How much each tree contributes to final prediction
                       # 0.01 = slow learning, needs many trees (more stable)
                       # 0.1 = moderate learning (good default)
                       # 0.3+ = fast learning, risky (overfit easily)
```

### Example Output
```
XGBoost Training:
  XGB Accuracy: 67.45%, Brier Score: 0.1641
```

---

## Model 3: Ensemble (Combined Model)

### What is Ensemble?
Combine both models to get the best of both:
- **LR** provides stability (won't go crazy with probabilities)
- **XGB** adds accuracy (catches patterns LR misses)

### Ensembling Code
```python
# Simple average of probabilities
ensemble_probs = (lr_probs + xgb_probs) / 2
# Example: (0.58 + 0.62) / 2 = 0.60 (60% home win probability)

# Convert to binary prediction (> 0.5 = home win)
ensemble_predictions = (ensemble_probs > 0.5).astype(int)

# Evaluate
ensemble_acc = accuracy_score(y_test, ensemble_predictions)
ensemble_brier = brier_score_loss(y_test, ensemble_probs)
```

### Example Output
```
Ensemble Results:
  Consolidated Accuracy: 67.89%, Brier Score: 0.1598
```

---

## Saved Model Bundle

### What Gets Saved?
```python
bundle = {
    'lr_model': lr_model,              # Trained LR model
    'xgb_model': xgb_model,            # Trained XGB model
    'scaler': scaler,                  # StandardScaler (for LR features)
    'features': features,              # Feature names list
    'weights': {'lr': 0.5, 'xgb': 0.5} # How to combine models
}

joblib.dump(bundle, 'cbb_predictor_bundle.joblib')
```

### File Size
- Typical size: 100-500 KB
- Contains all necessary info for predictions

---

## How to Use the Saved Model (Live Prediction)

### Loading the Bundle
```python
import joblib

bundle = joblib.load('cbb_predictor_bundle.joblib')
lr_model = bundle['lr_model']
xgb_model = bundle['xgb_model']
scaler = bundle['scaler']
features = bundle['features']
```

### Making a Prediction
```python
# Current live game state
current_game = {
    'score_diff': 5,           # Home +5
    'time_ratio': 0.875,       # 87.5% through game
    'mins_remaining': 2.5,     # 2.5 minutes left
    'period': 2                # Second half
}

# Convert to feature array
X_live = pd.DataFrame([current_game])[features]

# Scale for LR
X_live_scaled = scaler.transform(X_live)

# Get predictions
lr_prob = lr_model.predict_proba(X_live_scaled)[0, 1]   # 0.58
xgb_prob = xgb_model.predict_proba(X_live)[0, 1]        # 0.62

# Ensemble
home_win_prob = (lr_prob + xgb_prob) / 2                # 0.60 = 60%

print(f"Home team has {home_win_prob * 100:.1f}% win probability")
# Output: "Home team has 60.0% win probability"
```

---

## Data Example: Complete Flow

### Raw Game Event
```
Duke vs UNC, 2nd half, 5 minutes left
Duke: 45, UNC: 42
(Duke wins final score 48-45)
```

### Snapshot Created (collect_historical_data.py)
```csv
game_id,home_team,away_team,home_score,away_score,score_diff,period,mins_remaining,time_ratio,is_home_win
401547812,Duke,UNC,45,42,3,2,5,0.125,1
```

### Training Feature Vector (train_predictor.py)
```python
X = [3, 0.125, 5, 2]           # [score_diff, time_ratio, mins_remaining, period]
y = 1                          # Label: Duke won
```

### Model Prediction (at game time)
```python
# LR: "Given these features, 58% chance home wins"
# XGB: "Given these features, 62% chance home wins"
# Ensemble: (0.58 + 0.62) / 2 = 60% home win probability
```

---

## Common Variables Reference

### Game State Variables
```python
score_diff = home_score - away_score        # -20 to +20 typically
time_ratio = mins_remaining / 40.0          # 0.0 (end) to 1.0+ (OT)
mins_remaining = 0 to 20 (per period)       # Minutes left in current half
period = 1 (1st half) or 2 (2nd half)      # Can go 3+ for OT
```

### Model Output Variables
```python
lr_probs = [0.23, 0.67, 0.45, ...]         # LR probabilities (0.0-1.0)
xgb_probs = [0.31, 0.72, 0.49, ...]        # XGB probabilities (0.0-1.0)
ensemble_probs = (lr_probs + xgb_probs) / 2 # Combined probabilities
```

### Evaluation Variables
```python
accuracy_score      # % of correct predictions (0.0-1.0)
brier_score_loss    # Mean squared error of probabilities (0.0-1.0, lower better)
y_test              # Actual outcomes (0 or 1)
y_pred              # Predicted outcomes (0 or 1)
```

---

## Troubleshooting

### "Not enough data" Error
```
Error: Not enough data. Please collect more snapshots first.
```
**Solution**: Your CSV has < 100 rows. Run data collection for a longer date range.

### Accuracy is 50%
Means the model is no better than a coin flip. Reasons:
- Not enough training data (need 1000+ snapshots)
- Features don't predict the outcome well
- Try different time periods or collect more recent data

### Model takes too long to predict
- `n_estimators=100` might be too high; reduce to 50
- `max_depth=4` is fine; don't go higher

---

## Next Steps

1. **Run data collection**:
   ```bash
   python dashboard/scripts/collect_historical_data.py \
     --start 2024-11-01 --end 2025-03-01 --output training.csv
   ```

2. **Check output**:
   ```bash
   wc -l training.csv  # Should be 1000+ rows
   head training.csv   # View first few rows
   ```

3. **Train model**:
   ```bash
   python dashboard/scripts/train_predictor.py --input training.csv
   ```

4. **Check results**:
   - Look for "Consolidated Accuracy" close to 65%+
   - Model bundle saved to `cbb_predictor_bundle.joblib`

5. **Use in dashboard**:
   - Model is automatically loaded on app startup
   - Win probabilities appear in live games (if integration is enabled)

---

## Performance Tips

| Issue | Solution |
|-------|----------|
| Low accuracy | Collect more data (longer date range) |
| Training too slow | Reduce `n_estimators` from 100 to 50 |
| Overfitting (train 85%, test 55%) | Reduce `max_depth` or add more data |
| Predictions too extreme (0.1 or 0.9) | Use smaller `learning_rate` (0.05) |

