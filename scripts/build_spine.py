#!/usr/bin/env python3
"""
build_spine.py

Takes a sparse training table (one row only on days a zone had a sitrep entry)
and rebuilds it into a full, dense (nom x date) table suitable for training the
next-7-day case-onset classifier.

Usage:
    python scripts/build_spine.py training_table_final.csv --out training_table_spine.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ID_COLS = ["nom", "date"]

CUMULATIVE_COLS = [
    "cumulative_confirmed_cases",
    "cumulative_suspected_cases",
    "cumulative_suspected_deaths",
]

FLOW_COLS = [
    "new_confirmed_cases",
    "new_suspected_cases",
]

RECOMPUTED_COLS = ["rt_proxy", "rt_proxy_is_imputed"]
ROLL_WINDOW = 7


def build_backbone(df: pd.DataFrame) -> pd.DataFrame:
    """Create every zone x every day in the observed date range."""
    all_dates = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    all_zones = sorted(df["nom"].unique())
    backbone = pd.MultiIndex.from_product([all_zones, all_dates], names=["nom", "date"]).to_frame(index=False)
    return backbone


def fill_cumulative(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.sort_values(["nom", "date"])
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = df.groupby("nom")[col].ffill()
        df[col] = df[col].fillna(0)
    return df


def fill_flow(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = df[col].fillna(0)
    return df


def fill_static(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.sort_values(["nom", "date"])
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = df.groupby("nom")[col].ffill().bfill()
    return df


def recompute_rt_proxy(df: pd.DataFrame, new_case_col: str = "new_confirmed_cases") -> pd.DataFrame:
    """
    rt_proxy = (new cases in the trailing 7 days) / (new cases in the
    prior 7 days before that). Values > 1 indicate acceleration, < 1 indicate slowdown.
    It is flagged as imputed when there is insufficient history, or when the denominator is zero.
    """
    df = df.sort_values(["nom", "date"]).copy()
    g = df.groupby("nom")[new_case_col]

    trailing = g.transform(lambda s: s.rolling(ROLL_WINDOW, min_periods=ROLL_WINDOW).sum())
    prior = g.transform(lambda s: s.shift(ROLL_WINDOW).rolling(ROLL_WINDOW, min_periods=ROLL_WINDOW).sum())

    not_enough_history = trailing.isna() | prior.isna()
    zero_denominator = (~not_enough_history) & (prior == 0)

    with np.errstate(divide="ignore", invalid="ignore"):
        rt = trailing / prior

    rt = rt.where(~zero_denominator, 1.0)
    rt = rt.where(~not_enough_history, 1.0)

    df["rt_proxy"] = rt
    df["rt_proxy_is_imputed"] = not_enough_history | zero_denominator
    return df


def build_label(df: pd.DataFrame, new_case_col: str = "new_confirmed_cases") -> pd.DataFrame:
    """
    label_next_7d = 1 if there is >= 1 newly reported case in the 7 days after this row's date.
    label_censored = True when the 7-day forward window extends past the last observed date.
    """
    df = df.sort_values(["nom", "date"]).copy()
    max_date = df["date"].max()

    g = df.groupby("nom")[new_case_col]
    forward_sum = g.transform(lambda s: s[::-1].rolling(ROLL_WINDOW, min_periods=1).sum()[::-1].shift(-1))

    df["label_next_7d"] = (forward_sum.fillna(0) > 0).astype(int)
    df["label_censored"] = (df["date"] + pd.Timedelta(days=ROLL_WINDOW)) > max_date
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild a sparse zone-day table into a dense, model-ready spine.")
    parser.add_argument("input_csv", help="Path to the sparse training table CSV")
    parser.add_argument("--out", default="training_table_spine.csv", help="Output CSV path")
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    out_path = Path(args.out)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    print(f"Reading {input_path} ...")
    raw = pd.read_csv(input_path, parse_dates=["date"])
    print(f"  raw shape: {raw.shape}  |  zones: {raw['nom'].nunique()}  |  dates: {raw['date'].nunique()}")

    if "nom" not in raw.columns or "date" not in raw.columns:
        raise ValueError("Input CSV must contain 'nom' and 'date' columns")

    static_cols = [
        c for c in raw.columns if c not in ID_COLS + CUMULATIVE_COLS + FLOW_COLS + RECOMPUTED_COLS
    ]
    print(f"  cumulative cols: {CUMULATIVE_COLS}")
    print(f"  flow cols:       {FLOW_COLS}")
    print(f"  static cols:     {static_cols}")

    print("\nBuilding full (nom x date) backbone ...")
    backbone = build_backbone(raw)
    print(
        f"  backbone shape: {backbone.shape}  (vs raw {raw.shape[0]} rows -> "
        f"{backbone.shape[0] - raw.shape[0]} rows added)"
    )

    df = backbone.merge(raw, on=ID_COLS, how="left")

    print("\nFilling cumulative columns (forward-fill, then 0 before first report) ...")
    df = fill_cumulative(df, CUMULATIVE_COLS)

    print("Filling flow columns (0 on days with no sitrep entry) ...")
    df = fill_flow(df, FLOW_COLS)

    print("Broadcasting static columns across each zone's dates ...")
    df = fill_static(df, static_cols)

    print("\nRecomputing rt_proxy on the now-complete daily series ...")
    df = df.drop(columns=[c for c in RECOMPUTED_COLS if c in df.columns])
    df = recompute_rt_proxy(df)

    print("Building the non-leaky 7-day-ahead label ...")
    df = build_label(df)

    n_censored = int(df["label_censored"].sum())
    n_usable = int((~df["label_censored"]).sum())
    print(
        f"\nLabel coverage: {n_usable} usable rows, {n_censored} censored "
        "(forward window runs past last observed date)"
    )
    print("Class balance among usable rows:")
    print(df.loc[~df["label_censored"], "label_next_7d"].value_counts())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = df.sort_values(["nom", "date"]).reset_index(drop=True)
    df.to_csv(out_path, index=False)
    print(f"\nWrote dense spine table: {out_path}")
    print(f"Final shape: {df.shape[0]} rows x {df.shape[1]} columns")
    print("\nNOTE: filter out label_censored == True rows before training -- their true label isn't observable yet.")


if __name__ == "__main__":
    main()
