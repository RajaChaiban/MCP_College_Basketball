"""
Predictive Engine - Model Trainer (2025-26 safe pipeline).

Usage:
python dashboard/scripts/train_predictor.py --input cbb_training_data_real_2025_26.csv
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

# Ensure project root is importable when running as a script.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dashboard.scripts.leakage_safe_features import (
    add_contextual_features_leave_one_game_out,
)


FEATURES = [
    "score_diff",
    "momentum",
    "strength_diff",
    "time_ratio",
    "mins_remaining",
    "period",
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


def _assert_2025_26_input(path: Path) -> None:
    name = path.name.lower()
    if "2025_26" not in name and "2025-26" not in name:
        raise ValueError(
            "Input file must be 2025-26 data. Expected filename containing "
            "'2025_26' or '2025-26'."
        )


def _warn_data_quality(df: pd.DataFrame) -> None:
    if "game_id" in df.columns:
        games = int(df["game_id"].nunique())
        rows = len(df)
        print(f"Rows: {rows}, Unique games: {games}, Rows/game: {rows / max(1, games):.2f}")
    if "mins_remaining" in df.columns and df["mins_remaining"].nunique() <= 3:
        print(
            "WARNING: mins_remaining has very low cardinality. "
            "Dataset may not reflect minute-level live game progression."
        )
    if "time_ratio" in df.columns and df["time_ratio"].nunique() <= 3:
        print(
            "WARNING: time_ratio has very low cardinality. "
            "Model may underlearn timing dynamics."
        )


def _build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["momentum", "strength_diff", "time_ratio", "mins_remaining", "period"]:
        if col not in df.columns:
            df[col] = 0.0

    needed_ctx = {
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
    }
    if not needed_ctx.issubset(df.columns):
        print(
            "Contextual features missing or incomplete. "
            "Building leakage-safe contextual features..."
        )
        df = add_contextual_features_leave_one_game_out(df)

    return df.fillna(0)


def _split(df: pd.DataFrame):
    X = df[FEATURES]
    y = df["is_home_win"].astype(int)

    if "game_id" in df.columns:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(splitter.split(X, y, groups=df["game_id"]))
        split_mode = "group_by_game_id"
        return (
            X.iloc[train_idx],
            X.iloc[test_idx],
            y.iloc[train_idx],
            y.iloc[test_idx],
            split_mode,
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    return X_train, X_test, y_train, y_test, "row_random_no_group"


def train_models(input_csv: str, output_bundle: str = "cbb_predictor_bundle.joblib") -> None:
    path = Path(input_csv)
    _assert_2025_26_input(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    print(f"Loading data from {path}...")
    df_raw = pd.read_csv(path)
    if len(df_raw) < 100:
        raise ValueError("Not enough rows. Need at least 100 snapshots for stable training.")

    _warn_data_quality(df_raw)
    df = _build_feature_frame(df_raw)

    if not set(FEATURES).issubset(df.columns):
        missing = sorted(set(FEATURES) - set(df.columns))
        raise ValueError(f"Missing required features after preprocessing: {missing}")

    X_train, X_test, y_train, y_test, split_mode = _split(df)
    print(f"Using {len(FEATURES)} features.")
    print(f"Split mode: {split_mode}")
    print(f"Train rows: {len(X_train)}, Test rows: {len(X_test)}")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("Training Calibrated Logistic Regression...")
    lr_model = CalibratedClassifierCV(
        LogisticRegression(max_iter=1000),
        method="isotonic",
        cv=5,
    )
    lr_model.fit(X_train_scaled, y_train)
    lr_probs = lr_model.predict_proba(X_test_scaled)[:, 1]

    print("Training Calibrated XGBoost...")
    xgb_base = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        eval_metric="logloss",
    )
    xgb_model = CalibratedClassifierCV(xgb_base, method="isotonic", cv=5)
    xgb_model.fit(X_train, y_train)
    xgb_probs = xgb_model.predict_proba(X_test)[:, 1]

    ensemble_probs = 0.5 * lr_probs + 0.5 * xgb_probs
    ensemble_pred = (ensemble_probs > 0.5).astype(int)
    ensemble_acc = accuracy_score(y_test, ensemble_pred)
    ensemble_brier = brier_score_loss(y_test, ensemble_probs)
    ensemble_auc = roc_auc_score(y_test, ensemble_probs)

    print(f"Ensemble Accuracy: {ensemble_acc:.2%}")
    print(f"Ensemble Brier:    {ensemble_brier:.4f}")
    print(f"Ensemble ROC-AUC:  {ensemble_auc:.4f}")

    bundle = {
        "lr_model": lr_model,
        "xgb_model": xgb_model,
        "scaler": scaler,
        "features": FEATURES,
        "weights": {"lr": 0.5, "xgb": 0.5},
        "metadata": {
            "trained_at": pd.Timestamp.now().isoformat(),
            "season": "2025-2026",
            "features_used": FEATURES,
            "num_features": len(FEATURES),
            "split_mode": split_mode,
            "rows": int(len(df)),
            "unique_games": (
                int(df["game_id"].nunique()) if "game_id" in df.columns else None
            ),
            "brier_score": float(ensemble_brier),
            "ensemble_accuracy": float(ensemble_acc),
            "roc_auc": float(ensemble_auc),
            "data_source": str(path.name),
            "contextual_features_method": "leave_one_game_out",
        },
    }

    joblib.dump(bundle, output_bundle)
    print(f"Saved calibrated bundle to {output_bundle}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="cbb_training_data_real_2025_26.csv",
        help="Input CSV path. Must be 2025-26 data.",
    )
    parser.add_argument(
        "--output",
        default="cbb_predictor_bundle.joblib",
        help="Output bundle path.",
    )
    args = parser.parse_args()
    train_models(args.input, args.output)
