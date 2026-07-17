"""
EDA + correlation/multicollinearity check on training_table.csv.

What this does:
  1. Drops the national_* leftover columns -- these are structurally
     always-missing in a zone-level table (national totals only ever
     appeared on the rows already split into insp_sitrep_national_clean.csv
     back in clean_insp_sitrep.py), not real sparse data to explain away.
  2. Prints summary stats + missingness for the remaining columns.
  3. Computes a correlation matrix on numeric features and saves it as a
     heatmap -- specifically to catch multicollinearity among the
     flowminder_short_trips__outflow_* columns (5 dated snapshots of
     what may be the same underlying signal) and among the insp_sitrep
     cumulative/new case-count pairs.
  4. Lists any feature pairs with |correlation| > 0.9 explicitly, since
     that's the actionable multicollinearity signal -- not just "look
     at the heatmap and guess."

Usage:
    python eda_correlation.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "output" / "training_table.csv"
OUT_MISSINGNESS_PATH = REPO_ROOT / "output" / "eda_missingness.png"
OUT_CORR_PATH = REPO_ROOT / "output" / "eda_correlation_heatmap.png"
OUT_CORR_CSV = REPO_ROOT / "output" / "eda_correlation_matrix.csv"

NATIONAL_PREFIX = "national_"  # structurally-missing leftover columns, drop outright
ID_COLS = ["nom", "date"]
HIGH_CORR_THRESHOLD = 0.9


def main():
    df = pd.read_csv(IN_PATH)
    print("Loaded:", df.shape)

    national_cols = [c for c in df.columns if c.startswith(NATIONAL_PREFIX)]
    df = df.drop(columns=national_cols)
    print(f"Dropped {len(national_cols)} structurally-missing national_* columns: {national_cols}")

    print("\n=== shape after drop ===", df.shape)

    print("\n=== missingness (%) after drop, remaining columns ===")
    missingness = (df.isna().mean() * 100).round(1).sort_values(ascending=False)
    print(missingness)

    fig, ax = plt.subplots(figsize=(10, 8))
    missingness.plot(kind="barh", ax=ax)
    ax.set_xlabel("% missing")
    ax.set_title("Missingness by column (training_table.csv, after dropping national_*)")
    plt.tight_layout()
    fig.savefig(OUT_MISSINGNESS_PATH, dpi=150)
    print(f"\nSaved: {OUT_MISSINGNESS_PATH}")

    # --- correlation matrix on numeric feature columns only ---
    numeric_df = df.drop(columns=ID_COLS).select_dtypes(include="number")
    corr = numeric_df.corr()
    corr.to_csv(OUT_CORR_CSV)
    print(f"Saved: {OUT_CORR_CSV}")

    fig, ax = plt.subplots(figsize=(16, 14))
    sns.heatmap(corr, cmap="coolwarm", center=0, vmin=-1, vmax=1,
                square=True, linewidths=0.3, ax=ax,
                cbar_kws={"shrink": 0.6})
    ax.set_title("Feature correlation matrix (training_table.csv)")
    plt.tight_layout()
    fig.savefig(OUT_CORR_PATH, dpi=150)
    print(f"Saved: {OUT_CORR_PATH}")

    # --- explicit high-correlation pairs, the actionable multicollinearity signal ---
    print(f"\n=== feature pairs with |correlation| > {HIGH_CORR_THRESHOLD} ===")
    pairs = []
    cols = corr.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            if pd.notna(r) and abs(r) > HIGH_CORR_THRESHOLD:
                pairs.append((cols[i], cols[j], round(r, 3)))
    pairs.sort(key=lambda x: -abs(x[2]))
    for a, b, r in pairs:
        print(f"  {a}  <->  {b}   r={r}")
    if not pairs:
        print("  none found above threshold")


if __name__ == "__main__":
    main()