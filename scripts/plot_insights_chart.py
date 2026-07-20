"""
Build the three required insight plots from insp_sitrep_zone_level_clean.csv:
  1. Epidemic curve (daily case counts over time)
  2. Health-zone case breakdown (which zones are driving the outbreak)
  3. Case-fatality ratio (CFR) trend over time

Data note: the brief asks for "the epidemic curve since April 2026," but
insp_sitrep health-zone data starts 2026-05-14 -- there is no April data
anywhere in this dataset (confirmed against the raw sitreps, not a bug in
our cleaning). The curve below starts at the earliest real data point,
2026-05-14, and this gap is stated explicitly rather than silently
starting later than the brief describes.

National-level rows (insp_sitrep_national_clean.csv) only start
2026-06-01, so daily totals here are built by SUMMING zone-level data
across all zones per date instead -- this covers the full 2026-05-14 to
2026-07-11 range rather than being limited to the sparser national rows.

Usage:
    python plot_insight_charts.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "output" / "insp_sitrep_zone_level_clean.csv"
OUT_DIR = REPO_ROOT / "output"

TOP_N_ZONES = 15


def main():
    df = pd.read_csv(IN_PATH, parse_dates=["date"])
    print("Loaded:", df.shape, " date range:", df["date"].min(), "-", df["date"].max())

    # --- 1. Epidemic curve: daily new confirmed + suspected cases, summed across zones ---
    daily = df.groupby("date")[["new_confirmed_cases", "new_suspected_cases"]].sum(min_count=1)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(daily.index, daily["new_confirmed_cases"], marker="o", label="New confirmed cases")
    ax.plot(daily.index, daily["new_suspected_cases"], marker="o", label="New suspected cases",
            linestyle="--", alpha=0.7)
    ax.set_title("Epidemic curve — daily new cases across all health zones\n"
                 "(data starts 2026-05-14; no April 2026 data exists in this dataset)")
    ax.set_xlabel("Date")
    ax.set_ylabel("New cases (summed across zones)")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "insight_epidemic_curve.png", dpi=150)
    print("Saved: insight_epidemic_curve.png")

    # --- 2. Health-zone case breakdown: top N zones by latest cumulative confirmed cases ---
    latest_by_zone = (
        df.sort_values("date")
        .groupby("nom")["cumulative_confirmed_cases"]
        .last()
        .dropna()
        .sort_values(ascending=False)
        .head(TOP_N_ZONES)
    )

    fig, ax = plt.subplots(figsize=(10, 7))
    latest_by_zone.sort_values().plot(kind="barh", ax=ax, color="firebrick")
    ax.set_title(f"Top {TOP_N_ZONES} health zones by cumulative confirmed cases\n"
                 f"(as of {df['date'].max().date()})")
    ax.set_xlabel("Cumulative confirmed cases")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "insight_zone_breakdown.png", dpi=150)
    print("Saved: insight_zone_breakdown.png")

    # --- 3. Case-fatality ratio (CFR) trend over time ---
    cumulative_daily = df.groupby("date")[["cumulative_confirmed_cases", "cumulative_confirmed_deaths"]].sum(min_count=1)
    cumulative_daily["cfr"] = cumulative_daily["cumulative_confirmed_deaths"] / cumulative_daily["cumulative_confirmed_cases"]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(cumulative_daily.index, cumulative_daily["cfr"] * 100, marker="o", color="darkorange")
    ax.set_title("Case-fatality ratio (CFR) trend over time")
    ax.set_xlabel("Date")
    ax.set_ylabel("CFR (%)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "insight_cfr_trend.png", dpi=150)
    print("Saved: insight_cfr_trend.png")

    print(f"\nFinal CFR ({df['date'].max().date()}): "
          f"{cumulative_daily['cfr'].iloc[-1]*100:.2f}%")


if __name__ == "__main__":
    main()