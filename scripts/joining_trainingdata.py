"""
Join the cleaned insp_sitrep, OSRM, Flowminder, and WorldPop outputs into
one per-zone-per-day training table.

Join logic:
  - insp_sitrep_training_window.csv and osrm_nearest_active_feature.csv
    are both keyed on (nom, date) -- joined directly on both.
  - flowminder_clean.csv and worldpop_merged.csv are keyed on nom ONLY
    (population and mobility snapshots don't vary by date in this data)
    -- joined on nom alone, which broadcasts each zone's value across
    every date row for that zone.
  - All joins are LEFT joins anchored on insp_sitrep_training_window.csv,
    since that's where the target variable and the (nom, date) index
    for the whole table come from. This intentionally allows NaNs to
    remain -- missingness strategy is decided AFTER this join, once the
    full combined picture is visible (see project notes), not before.

This script does NOT drop or impute anything -- that's a deliberate
follow-up step, not part of this join.

Usage:
    python join_training_table.py
"""
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "output"

SITREP_PATH = OUT_DIR / "insp_sitrep_training_window.csv"
OSRM_PATH = OUT_DIR / "osrm_nearest_active_feature.csv"
FLOWMINDER_PATH = OUT_DIR / "flowminder_clean.csv"
WORLDPOP_PATH = OUT_DIR / "worldpop_merged.csv"

OUT_PATH = OUT_DIR / "training_table.csv"


def main():
    sitrep = pd.read_csv(SITREP_PATH, parse_dates=["date"])
    osrm = pd.read_csv(OSRM_PATH, parse_dates=["date"])
    flowminder = pd.read_csv(FLOWMINDER_PATH)
    worldpop = pd.read_csv(WORLDPOP_PATH)

    print("insp_sitrep_training_window:", sitrep.shape)
    print("osrm_nearest_active_feature:", osrm.shape)
    print("flowminder_clean:", flowminder.shape)
    print("worldpop_merged:", worldpop.shape)

    # anchor on sitrep (nom, date) -- this defines the row index for the
    # whole table
    df = sitrep.merge(osrm, on=["nom", "date"], how="left")
    print("\nafter joining osrm:", df.shape,
          f"({df['min_minutes_to_active_zone'].isna().sum()} rows with no OSRM value)")

    df = df.merge(flowminder, on="nom", how="left")
    flow_cols = [c for c in flowminder.columns if c != "nom"]
    print("after joining flowminder:", df.shape,
          f"({df[flow_cols].isna().all(axis=1).sum()} rows with no Flowminder data at all)")

    df = df.merge(worldpop, on="nom", how="left")
    print("after joining worldpop:", df.shape,
          f"({df['pop_count'].isna().sum()} rows with no population value)")

    df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved: {OUT_PATH}")
    print("final shape:", df.shape)
    print("columns:", list(df.columns))

    print("\n=== missingness summary (share of rows missing, per column) ===")
    print((df.isna().mean() * 100).round(1).sort_values(ascending=False))


if __name__ == "__main__":
    main()