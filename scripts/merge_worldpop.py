"""
Merge every worldpop__*.csv file in build/long/ into a single zone-keyed table.

Note: build/long/*.csv files have NO header row (unlike data/*/processed/*.csv,
which do) -- just bare `zone,value` rows, UTF-8 BOM-prefixed. Column names are
assigned here from each file's own name, not read from the file.

Run from the repo root:
    python scripts/merge_worldpop.py
"""
import glob
from pathlib import Path

import pandas as pd

IN_DIR = Path("data/external/BDBV2026-Data/build/long")
OUT_PATH = Path("output/worldpop_merged.csv")
PATTERN = "worldpop__*.csv"


def main():
    files = sorted(IN_DIR.glob(PATTERN))
    if not files:
        raise FileNotFoundError(f"No files matching {PATTERN} in {IN_DIR}")

    merged = None
    for f in files:
        # metric name from filename, e.g. worldpop__pop_count.csv -> pop_count
        metric = f.stem.replace("worldpop__", "")
        df = pd.read_csv(f, header=None, names=["nom", metric], encoding="utf-8-sig")
        print(f"{f.name}: {df.shape[0]} rows -> column '{metric}'")

        merged = df if merged is None else merged.merge(df, on="nom", how="outer")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_PATH, index=False)
    print(f"\nSaved: {OUT_PATH}")
    print("shape:", merged.shape)
    print("columns:", list(merged.columns))


if __name__ == "__main__":
    main()