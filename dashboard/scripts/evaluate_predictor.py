"""
Evaluate CBB predictor bundle with game-aware metrics.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split


def _load_eval_split(df: pd.DataFrame, features: list[str]):
    X = df[features]
    y = df["is_home_win"].astype(int)
    if "game_id" in df.columns:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        tr, te = next(splitter.split(X, y, groups=df["game_id"]))
        return X.iloc[te], y.iloc[te], "group_by_game_id"
    _, X_te, _, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    return X_te, y_te, "row_random_no_group"


def evaluate(bundle_path: str, data_path: str) -> None:
    bundle = joblib.load(bundle_path)
    features = bundle["features"]
    scaler = bundle["scaler"]
    lr = bundle["lr_model"]
    xgb = bundle["xgb_model"]

    df = pd.read_csv(data_path).fillna(0)
    missing = sorted(set(features) - set(df.columns))
    if missing:
        raise ValueError(f"Missing features in eval data: {missing}")

    X_te, y_te, split_mode = _load_eval_split(df, features)
    X_te_scaled = scaler.transform(X_te)
    probs = 0.5 * lr.predict_proba(X_te_scaled)[:, 1] + 0.5 * xgb.predict_proba(X_te)[:, 1]
    pred = (probs > 0.5).astype(int)

    print(f"Split mode: {split_mode}")
    print(f"Eval rows: {len(X_te)}")
    print(f"Accuracy:  {accuracy_score(y_te, pred):.4f}")
    print(f"Brier:     {brier_score_loss(y_te, probs):.4f}")
    print(f"Log Loss:  {log_loss(y_te, probs, labels=[0, 1]):.4f}")
    print(f"ROC-AUC:   {roc_auc_score(y_te, probs):.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default="cbb_predictor_bundle_2025_26_safe.joblib")
    parser.add_argument("--data", default="enhanced_training_data_2025_26_safe.csv")
    args = parser.parse_args()
    evaluate(args.bundle, args.data)
