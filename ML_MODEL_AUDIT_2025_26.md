# ML Model Audit Report — 2025-26 Season Data Verification

**Date:** March 1, 2026
**Status:** ⚠️ MIXED - REQUIRES CLEANUP

---

## Executive Summary

Your ML models are **mostly on 2025-26 season data**, but there are several files and default configurations that reference old data or lack clear season specifications. This audit identifies issues and provides cleanup steps.

### Key Findings

| Item | Status | Notes |
|------|--------|-------|
| **Current Production Model** | ✓ CORRECT | Trained on 2025-26 only (Mar 1, 2026) |
| **Enhanced Training Data** | ✓ CORRECT | 1,988 snapshots from 2025-26 games |
| **Real Training Data** | ✓ CORRECT | 1,988 snapshots from 2025-26 games |
| **Old Training Data** | ❌ OBSOLETE | Synthetic test data, should be removed |
| **Data Collection Scripts** | ⚠️ MIXED | One is hardcoded to old dates |
| **Documentation** | ⚠️ OUTDATED | References old default data paths |

---

## Detailed Findings

### 1. Current Production Model ✓ CORRECT

**File:** `cbb_predictor_bundle.joblib`
**Size:** 448 KB
**Trained:** 2026-03-01 00:36:46
**Data Source:** `enhanced_training_data_2025_26.csv`
**Features:** 18 (6 original + 12 contextual)
**Accuracy:** 99.75%
**Brier Score:** 0.0016

**Metadata Confirms:**
```
trained_at: 2026-03-01T00:36:46.400034
data_source: enhanced_training_data_2025_26.csv
num_features: 18
ensemble_accuracy: 0.9974874371859297
```

**Status:** ✓ Production ready, 100% 2025-26 data

---

### 2. Training Data Files

#### A. `enhanced_training_data_2025_26.csv` ✓ CORRECT
- **Size:** 404 KB
- **Rows:** 1,989 (1 header + 1,988 snapshots)
- **Columns:** 24 (original 12 + 12 new contextual features)
- **Data Source:** Real 2025-26 season games
- **Date Range:** Nov 2025 - Feb 27, 2026
- **Status:** ✓ Current, production-ready

#### B. `cbb_training_data_real_2025_26.csv` ✓ CORRECT
- **Size:** 245 KB
- **Rows:** 1,989 (1 header + 1,988 snapshots)
- **Columns:** 12 (original features only)
- **Data Source:** Real 2025-26 season games
- **Date Range:** Nov 2025 - Feb 27, 2026
- **Game Count:** 994 unique games
- **Status:** ✓ Valid, base data for enhancement

#### C. `cbb_training_data.csv` ❌ OBSOLETE
- **Size:** 16 KB
- **Rows:** 201 (1 header + 200 snapshots)
- **Columns:** 10 (basic features only)
- **Game IDs:** 0-200 (synthetic/test data)
- **Date Info:** NONE (no date column)
- **Status:** ❌ OBSOLETE - Should be removed/archived

**What is this file?**
```
game_id,home_score,away_score,period,mins_remaining,time_ratio,strength_diff,momentum,is_home_win,score_diff
0,53,65,1,11,0.354810...,3.065619...,2.838215...,0,-12
1,45,71,1,15,0.476098...,1.231258...,0.543212...,0,-26
...
```
This is synthetic/test data. Game IDs are simple integers (0-200) with no real basketball context. Should NOT be used for training.

#### D. `season_games_2025_26.csv` ✓ CORRECT
- **Size:** 244 KB
- **Rows:** 1,989
- **Status:** ✓ Copy of real_2025_26 data (used for feature extraction)

---

### 3. Data Collection Scripts

#### A. `collect_real_2025_26_data.py` ✓ CORRECT
- **Purpose:** Collects real 2025-26 season data
- **Date Range:** Hardcoded to Nov 1, 2025 - Feb 27, 2026
- **Output:** `cbb_training_data_real_2025_26.csv`
- **Status:** ✓ Correct, 2025-26 only

```python
start = datetime.strptime("2025-11-01", "%Y-%m-%d")
end = datetime.strptime("2026-02-27", "%Y-%m-%d")
```

#### B. `collect_historical_data.py` ⚠️ MIXED
- **Purpose:** General-purpose data collection
- **Date Range:** Accepts arguments (--start, --end)
- **Default Range:** Comments show 2024-11-01 to 2025-03-01 (OLD 2024-25)
- **Status:** ⚠️ Dangerous default, needs update

**Current default in docstring:**
```python
"""
Usage: python dashboard/scripts/collect_historical_data.py --start 2024-11-01 --end 2025-03-01 --output training_data.csv
"""
```

**Risk:** If someone runs this without arguments, it will try to collect 2024-25 season data!

```python
parser.add_argument("--input", default="cbb_training_data.csv", ...)
parser.add_argument("--output", default="cbb_training_data.csv", ...)
```

---

### 4. Training Script Configuration

**File:** `dashboard/scripts/train_predictor.py`

**Default Input:** `cbb_training_data.csv` (the obsolete file!)

```python
parser.add_argument("--input", default="cbb_training_data.csv", help="Input CSV path")
```

**Current Usage:** Safe (we explicitly use `enhanced_training_data_2025_26.csv`)
**Problem:** If someone runs without arguments, defaults to obsolete file

---

### 5. Documentation References

**Files with outdated defaults:**
- `CLAUDE.md` — References `cbb_training_data.csv`
- `PREDICTOR_GUIDE.md` — References old 2024-25 dates
- `README.md` — References `cbb_training_data.csv`
- `dashboard/scripts/collect_historical_data.py` — Docstring shows 2024-25 dates

---

## Recommendations (Priority Order)

### PRIORITY 1: Delete Obsolete Files ✓ DO THIS NOW

Delete these files to prevent accidental use of wrong data:

```bash
rm cbb_training_data.csv
rm cbb_training_data_2025_26.csv  # Empty placeholder, not needed
```

**Why:** These are confusing and could cause old/wrong data to be used.

---

### PRIORITY 2: Update Script Defaults

#### Update `collect_historical_data.py`

**Change docstring from:**
```python
"""
Usage: python dashboard/scripts/collect_historical_data.py --start 2024-11-01 --end 2025-03-01 --output training_data.csv
"""
```

**To:**
```python
"""
Usage: python dashboard/scripts/collect_historical_data.py --start 2025-11-01 --end 2026-03-01 --output cbb_training_data_2025_26.csv

NOTE: This script collects historical data for a custom date range.
For current season (2025-26), use: collect_real_2025_26_data.py instead.
"""
```

**Change default output:**
```python
parser.add_argument("--output", default="cbb_training_data_2025_26.csv", help="Output CSV path")
```

#### Update `train_predictor.py` default

**Change from:**
```python
parser.add_argument("--input", default="cbb_training_data.csv", help="Input CSV path")
```

**To:**
```python
parser.add_argument("--input", default="enhanced_training_data_2025_26.csv", help="Input CSV path (should be 2025-26 season)")
```

---

### PRIORITY 3: Update Documentation

#### `CLAUDE.md`
**Change:**
```
Run: `python dashboard/scripts/train_predictor.py --input cbb_training_data.csv`
```

**To:**
```
Run: `python dashboard/scripts/train_predictor.py --input enhanced_training_data_2025_26.csv`

For 2025-26 season, use the enhanced data with contextual features for best accuracy (99.75%).
```

#### `README.md`
Update similar references to use correct file paths.

---

## Data Lineage for Current Production Model

```
Real 2025-26 Season Games (Nov 2025 - Feb 27, 2026)
       ↓
cbbpy ESPN API
       ↓
cbb_training_data_real_2025_26.csv (1,988 snapshots)
       ↓
Feature Extraction (12 contextual features)
       ↓
enhanced_training_data_2025_26.csv (1,988 snapshots with 18 features)
       ↓
Model Training
       ├─ Logistic Regression (99.50% accuracy)
       ├─ XGBoost (99.75% accuracy)
       └─ Ensemble (99.75% accuracy)
       ↓
cbb_predictor_bundle.joblib (CURRENT PRODUCTION MODEL)
       ↓
Dashboard (Loaded on startup, used for Gemini predictions)
```

---

## Verification Checklist

Run this to verify all models are 2025-26:

```bash
# 1. Check current model
python -c "
import joblib
bundle = joblib.load('cbb_predictor_bundle.joblib')
print('✓ Current model data source:', bundle['metadata']['data_source'])
print('✓ Model accuracy:', f\"{bundle['metadata']['ensemble_accuracy']:.1%}\")
print('✓ Model trained:', bundle['metadata']['trained_at'])
"

# 2. Check training data
wc -l enhanced_training_data_2025_26.csv
# Should show: 1989 rows (1 header + 1988 snapshots from 994 games)

# 3. Check for obsolete files
ls -la cbb_training_data.csv  # Should NOT exist after cleanup
```

---

## Summary Table

| Component | Current Status | Data Season | Action Needed |
|-----------|---|---|---|
| **Production Model Bundle** | ✓ CORRECT | 2025-26 | None |
| **Enhanced Training Data** | ✓ CORRECT | 2025-26 | Keep |
| **Real Training Data** | ✓ CORRECT | 2025-26 | Keep as backup |
| **Obsolete Test Data** | ❌ OBSOLETE | Synthetic | DELETE |
| **Collection Script (Real)** | ✓ CORRECT | 2025-26 | None |
| **Collection Script (Historical)** | ⚠️ MIXED | Configurable | Update defaults |
| **Training Script** | ⚠️ MIXED | Configurable | Update defaults |
| **Documentation** | ⚠️ OUTDATED | Mixed | Update references |

---

## Bottom Line

✓ **Your current model is 100% 2025-26 season data**

⚠️ **But cleanup is needed to prevent future mistakes:**
1. Delete obsolete test data
2. Update script defaults to 2025-26
3. Update documentation to match

**Estimated cleanup time:** 15 minutes

---

## After Cleanup

Once you run the cleanup commands, your system will be:
- ✓ 100% 2025-26 season for all models
- ✓ No obsolete test files
- ✓ Safe defaults in scripts
- ✓ Clear documentation
