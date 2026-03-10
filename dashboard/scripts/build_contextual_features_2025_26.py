"""
Build leakage-safe contextual features for 2025-26 training snapshots.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

# Ensure project root is importable when running as a script.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dashboard.scripts.leakage_safe_features import (
    add_contextual_features_leave_one_game_out,
)


def build(input_csv: str, output_csv: str) -> None:
    in_path = Path(input_csv)
    out_path = Path(output_csv)
    name = in_path.name.lower()
    if "2025_26" not in name and "2025-26" not in name:
        raise ValueError("Input must be 2025-26 data.")

    df = pd.read_csv(in_path)
    out = add_contextual_features_leave_one_game_out(df)
    out.to_csv(out_path, index=False)
    print(f"Saved: {out_path}")
    print(f"Rows: {len(out)} | Cols: {len(out.columns)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="cbb_training_data_real_2025_26.csv")
    parser.add_argument("--output", default="enhanced_training_data_2025_26_safe.csv")
    args = parser.parse_args()
    build(args.input, args.output)
