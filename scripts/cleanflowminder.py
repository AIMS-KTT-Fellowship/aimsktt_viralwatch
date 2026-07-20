"""
Clean flowminder_merged.csv into a usable feature table.

What this fixes, and why:
  1. Every "__static" column is an exact duplicate of its "bare" counterpart
     (confirmed byte-identical within float tolerance) -- the merge pulled
     the same metric in from two source representations. Keep only the bare
     version.
  2. "__static.matrix" columns are near-empty artifacts (as low as 4-5
     non-null values out of ~470 rows) -- drop them.
  3. Scope creep: this file includes the full flowminder__inflow/outflow
     dataset (4 columns), even though the team decided to use only
     flowminder_short_trips. Dropped here to match that decision --
     re-add if the team decides otherwise.
  4. ~52 of 519 health zones have NO flowminder data at all (not missing
     values -- absent rows). Expected for a mobile-subscriber-density
     dataset (low-coverage rural zones), but treat as structurally
     missing when joining downstream, not as zero.

Usage:
    python clean_flowminder.py
"""
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "output" / "flowminder_merged.csv"
OUT_PATH = REPO_ROOT / "output" / "flowminder_clean.csv"

DROP_SUFFIXES = ("__static", ".matrix")
KEEP_PREFIX = "flowminder_short_trips__"  # drop plain flowminder__ (scope decision)


def main():
    df = pd.read_csv(IN_PATH)

    # coerce every metric column to numeric -- the raw merge mixes types
    for col in df.columns:
        if col != "nom":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # sanity-check the assumption that bare/__static pairs are true duplicates
    # before dropping -- fail loudly if a future re-merge changes that
    import numpy as np
    bases = {
        c.replace("__static", "")
        for c in df.columns
        if c.endswith("__static") and not c.endswith(".matrix")
    }
    for b in bases:
        s = b + "__static"
        if b in df.columns and s in df.columns:
            both = df[[b, s]].dropna()
            if len(both) and not np.isclose(both[b], both[s]).all():
                raise ValueError(
                    f"Assumption broken: '{b}' and '{s}' are no longer "
                    "identical -- inspect before dropping either column."
                )

    keep_cols = ["nom"] + [
        c for c in df.columns
        if c.startswith(KEEP_PREFIX) and not c.endswith(DROP_SUFFIXES)
    ]
    clean = df[keep_cols].copy()

    dropped = set(df.columns) - set(keep_cols)
    print(f"Dropped {len(dropped)} columns (duplicates/artifacts/out-of-scope):")
    for c in sorted(dropped):
        print(" -", c)

    clean.to_csv(OUT_PATH, index=False)
    print(f"\nSaved: {OUT_PATH}")
    print("shape:", clean.shape)
    print("columns:", list(clean.columns))
    print("zones with at least one non-null metric:", clean.set_index("nom").notna().any(axis=1).sum())


if __name__ == "__main__":
    main()