"""
Clean insp_sitrep_merged.csv (the outer-joined result of all 31 insp_sitrep
files) into a usable training table for the anomaly-detection proof point.

What this does, and why:
  1. Fix dtypes -- "ND" (INSP's own "no data" code) is mixed into every
     numeric column, forcing pandas to read them all as text.
  2. Split out national-total rows -- 36 rows have no `nom` because they're
     national rollups, not zone data. They don't belong in a per-zone table.
  3. Flag/drop rows with missing `date` -- a genuine ambiguous-date case
     (Nyankunde), document rather than silently dropping.
  4. Scope to the window where the target variable (new_suspected_cases)
     actually has health-zone-level coverage: 2026-05-14 to 2026-05-29.
     Suspected-case reporting at zone level stops being published after
     that -- this is a real gap in what INSP released, not a bug in the
     join, and it's the pre-confirmation signal the project's anomaly
     detection proof point depends on (confirmed cases can't substitute,
     since they ARE the confirmation, not a signal preceding it).

Usage:
    python clean_insp_sitrep.py
"""
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "output" / "insp_sitrep_merged.csv"
OUT_ZONE_PATH = REPO_ROOT / "output" / "insp_sitrep_zone_level_clean.csv"
OUT_NATIONAL_PATH = REPO_ROOT / "output" / "insp_sitrep_national_clean.csv"
OUT_TRAINING_PATH = REPO_ROOT / "output" / "insp_sitrep_training_window.csv"

TARGET_COL = "new_suspected_cases"
TRAINING_WINDOW = ("2026-05-14", "2026-05-29")  # inclusive, matches target coverage

ID_COLS = ["nom", "date"]
NATIONAL_COLS_ONLY_PATTERN = "national_"  # columns like national_cumulative_confirmed_cases


def load_and_fix_dtypes(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    non_id_cols = [c for c in df.columns if c not in ID_COLS]
    for col in non_id_cols:
        df[col] = df[col].replace("ND", pd.NA)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def split_national_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rows with nom missing are national rollups, not zone data."""
    national_rows = df[df["nom"].isna()].copy()
    zone_rows = df[df["nom"].notna()].copy()
    return zone_rows, national_rows


def flag_missing_dates(df: pd.DataFrame) -> pd.DataFrame:
    missing = df[df["date"].isna()]
    if len(missing):
        print(f"!! {len(missing)} row(s) with missing date -- documenting, not silently dropping:")
        print(missing[["nom"] + [c for c in df.columns if df.loc[missing.index, c].notna().any()
                                  and c not in ("nom", "date")]])
    return df[df["date"].notna()].copy()


def main():
    df = load_and_fix_dtypes(IN_PATH)
    print("Loaded:", df.shape)

    zone_rows, national_rows = split_national_rows(df)
    print(f"Split: {len(zone_rows)} zone-level rows, {len(national_rows)} national-total rows")

    zone_rows = flag_missing_dates(zone_rows)

    zone_rows.to_csv(OUT_ZONE_PATH, index=False)
    national_rows.to_csv(OUT_NATIONAL_PATH, index=False)
    print(f"Saved zone-level table: {OUT_ZONE_PATH} ({zone_rows.shape})")
    print(f"Saved national-total table: {OUT_NATIONAL_PATH} ({national_rows.shape})")

    # --- scoped training window ---
    start, end = TRAINING_WINDOW
    in_window = zone_rows[(zone_rows["date"] >= start) & (zone_rows["date"] <= end)]

    target_coverage = in_window[TARGET_COL].notna().mean()
    print(f"\n=== training window {start} to {end} ===")
    print("rows:", len(in_window), " zones:", in_window["nom"].nunique())
    print(f"target ('{TARGET_COL}') non-null rate in this window: {target_coverage:.1%}")

    in_window.to_csv(OUT_TRAINING_PATH, index=False)
    print(f"Saved training window table: {OUT_TRAINING_PATH}")


if __name__ == "__main__":
    main()