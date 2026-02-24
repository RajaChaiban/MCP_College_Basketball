"""
Predictive Engine — Model Trainer.
Usage: python dashboard/scripts/train_predictor.py --input cbb_training_data.csv

Trains two models: 
1. Logistic Regression (Stable Anchor)
2. XGBoost (Nuanced Patterns)

Consolidates them into a single predictive percentage.
"""

import argparse
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, brier_score_loss

def train_models(input_csv: str):
    # 1. Load Data
    print(f"Loading data from {input_csv}...")
    df = pd.read_csv(input_csv)
    
    if len(df) < 100:
        print("Error: Not enough data. Please collect more snapshots first.")
        return

    # 2. Feature Selection
    # X = [score_diff, time_ratio, mins_remaining, period]
    # y = is_home_win
    features = ['score_diff', 'time_ratio', 'mins_remaining', 'period']
    X = df[features]
    y = df['is_home_win']

    # 3. Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # --- MODEL 1: Logistic Regression ---
    # Needs scaling for best performance
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("Training Logistic Regression (Anchor Model)...")
    lr_model = LogisticRegression()
    lr_model.fit(X_train_scaled, y_train)
    
    lr_probs = lr_model.predict_proba(X_test_scaled)[:, 1]
    lr_acc = accuracy_score(y_test, lr_model.predict(X_test_scaled))
    lr_brier = brier_score_loss(y_test, lr_probs) # Low is better
    print(f"  LR Accuracy: {lr_acc:.2%}, Brier Score: {lr_brier:.4f}")

    # --- MODEL 2: XGBoost ---
    # Handles raw values, good for non-linearities
    print("Training XGBoost (Nuance Model)...")
    xgb_model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    xgb_model.fit(X_train, y_train)
    
    xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
    xgb_acc = accuracy_score(y_test, xgb_model.predict(X_test))
    xgb_brier = brier_score_loss(y_test, xgb_probs)
    print(f"  XGB Accuracy: {xgb_acc:.2%}, Brier Score: {xgb_brier:.4f}")

    # 4. Consolidation (Ensembling)
    # We simple average the probabilities for now
    ensemble_probs = (lr_probs + xgb_probs) / 2
    ensemble_acc = accuracy_score(y_test, (ensemble_probs > 0.5).astype(int))
    ensemble_brier = brier_score_loss(y_test, ensemble_probs)
    print(f"Consolidated Accuracy: {ensemble_acc:.2%}, Brier Score: {ensemble_brier:.4f}")

    # 5. Save Everything
    # We save a bundle: (LR model, XGB model, Scaler, Weights)
    bundle = {
        'lr_model': lr_model,
        'xgb_model': xgb_model,
        'scaler': scaler,
        'features': features,
        'weights': {'lr': 0.5, 'xgb': 0.5}
    }
    
    joblib.dump(bundle, 'cbb_predictor_bundle.joblib')
    print("Predictor bundle saved to cbb_predictor_bundle.joblib")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="cbb_training_data.csv", help="Input CSV path")
    args = parser.parse_args()
    
    train_models(args.input)
