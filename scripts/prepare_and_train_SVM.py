"""
End-to-end: compute Rt-proxy, trim/clean features, then fit the
One-Class SVM. Combines what were three separate scripts
(compute_rt_proxy.py, prepare_final_table.py, fit_oneclass_svm.py) into
one, since they're always run together as a single pipeline.

See each function's docstring for the reasoning behind that step -- the
short version:
  1. Rt-proxy: vectorised NumPy rolling-window case-growth ratio per zone.
     Only ~29% of final rows get a real computed value (needs history);
     rest imputed as neutral (Rt=1), flagged via rt_proxy_is_imputed.
  2. Trim: drop confirmed near-duplicate columns (flowminder __static
     copies, total_poe_* copies) and national_* leftover columns.
  3. Missingness: drop >70%-missing columns, forward-fill cumulative_*
     per zone (matches INSP's own convention), drop rows missing the
     target, drop two secondary/low-value column groups rather than
     losing more rows to them, impute remaining Flowminder gaps as 0,
     final rows-with-any-NaN cleanup.
  4. Model: temporal (not random) train/test split -- required for
     One-Class SVM, which needs to train on "normal" and test on a
     later period, not a random mix of both. NOTE: the train period
     used here is NOT a genuine pre-outbreak baseline (none exists in
     any of the 7 provided data sources -- checked and documented in
     output/README.md) -- it's the earliest available adaptation.

Usage:
    python prepare_and_train_svm.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "output"

ZONE_LEVEL_PATH = OUT_DIR / "insp_sitrep_zone_level_clean.csv"
TRAINING_TABLE_PATH = OUT_DIR / "training_table.csv"
RT_PROXY_OUT_PATH = OUT_DIR / "rt_proxy_feature.csv"
FINAL_TABLE_PATH = OUT_DIR / "training_table_final.csv"
SVM_OUT_PATH = OUT_DIR / "svm_flagged_anomalies.csv"

TAU_DAYS = 4

COLLINEAR_DROP_COLS = [
    "total_poe_hand_washing", "total_poe_passed", "total_poe_sanitised",
    "total_poe_refused_hand_washing",
    "flowminder_short_trips__outflow_20260430",
    "flowminder_short_trips__outflow_20260507",
    "flowminder_short_trips__outflow_20260514",
    "flowminder_short_trips__outflow_20260521",
    "flowminder_short_trips__ituri_subscriber_days_prior_20260503",
    "flowminder_short_trips__nk_subscriber_days_prior_20260503",
]
NATIONAL_PREFIX = "national_"

HIGH_MISSING_THRESHOLD = 0.70
TARGET_COL = "new_suspected_cases"
DROP_SECONDARY_COLS = [
    "new_contacts_listed", "cumulative_contacts_traced",
    "cumulative_confirmed_deaths", "new_suspected_deaths",
]
FLOWMINDER_PREFIX = "flowminder_short_trips__"

RATE_SOURCE_COLS = [
    "new_suspected_cases", "new_confirmed_cases",
    "cumulative_suspected_cases", "cumulative_confirmed_cases",
]
FEATURE_COLS = [
    "new_suspected_cases_rate", "new_confirmed_cases_rate",
    "cumulative_suspected_cases_rate", "cumulative_confirmed_cases_rate",
    "cumulative_suspected_deaths",
    "min_minutes_to_active_zone",
    "flowminder_short_trips__ituri_subscriber_days_followup_20260608",
    "flowminder_short_trips__nk_subscriber_days_followup_20260608",
    "flowminder_short_trips__outflow_20260524",
    "pop_density",
    "rt_proxy",
]
SPLIT_DATE = "2026-05-26"
SVM_GAMMA = 0.005
SVM_NU = 0.05


# ---------------------------------------------------------------------
# Step 1: Rt-proxy
# ---------------------------------------------------------------------

def compute_rt_for_zone(dates: pd.Series, cumulative: pd.Series) -> pd.DataFrame:
    """Vectorised Rt-proxy for a single zone's time series: ratio of new
    cases in a trailing tau-day window to the tau-day window before it."""
    full_range = pd.date_range(dates.min(), dates.max(), freq="D")
    s = pd.Series(cumulative.values, index=dates.values).reindex(full_range).ffill()

    cum = s.to_numpy(dtype=float)
    new_cases = np.diff(cum, prepend=cum[0])
    new_cases = np.clip(new_cases, a_min=0, a_max=None)

    kernel = np.ones(TAU_DAYS)
    window_sum = np.convolve(new_cases, kernel, mode="full")[:len(new_cases)]
    prev_window_sum = np.roll(window_sum, TAU_DAYS)
    prev_window_sum[:TAU_DAYS] = np.nan

    with np.errstate(divide="ignore", invalid="ignore"):
        rt_proxy = np.where(prev_window_sum > 0, window_sum / prev_window_sum, np.nan)

    return pd.DataFrame({"date": full_range, "rt_proxy": rt_proxy})


def compute_rt_proxy() -> pd.DataFrame:
    df = pd.read_csv(ZONE_LEVEL_PATH, parse_dates=["date"])
    df = df.dropna(subset=["cumulative_suspected_cases"])

    results = []
    for nom, group in df.groupby("nom"):
        group = group.sort_values("date")
        if group["date"].nunique() < TAU_DAYS * 2:
            continue
        rt_df = compute_rt_for_zone(group["date"], group["cumulative_suspected_cases"])
        rt_df["nom"] = nom
        results.append(rt_df)

    result = pd.concat(results, ignore_index=True)[["nom", "date", "rt_proxy"]]
    result.to_csv(RT_PROXY_OUT_PATH, index=False)
    print(f"[Step 1] Rt-proxy computed for {result['nom'].nunique()} zones, "
          f"{result['rt_proxy'].notna().sum()}/{len(result)} rows have a real value")
    return result


# ---------------------------------------------------------------------
# Step 2: trim + missingness + merge Rt-proxy
# ---------------------------------------------------------------------

def trim_features(df: pd.DataFrame) -> pd.DataFrame:
    national_cols = [c for c in df.columns if c.startswith(NATIONAL_PREFIX)]
    all_drop = COLLINEAR_DROP_COLS + national_cols
    missing = [c for c in all_drop if c not in df.columns]
    if missing:
        raise ValueError(f"Expected columns not found: {missing}")
    df = df.drop(columns=all_drop)
    print(f"[Step 2.1] Dropped {len(all_drop)} collinear/national columns -> shape {df.shape}")
    return df


def handle_missingness(df: pd.DataFrame) -> pd.DataFrame:
    high_missing = df.isna().mean() > HIGH_MISSING_THRESHOLD
    df = df.drop(columns=high_missing[high_missing].index.tolist())

    cum_cols = [c for c in df.columns if c.startswith("cumulative_")]
    df = df.sort_values(["nom", "date"])
    df[cum_cols] = df.groupby("nom")[cum_cols].ffill()

    before = len(df)
    df = df[df[TARGET_COL].notna()].copy()
    print(f"[Step 2.2] Dropped rows missing target: {before} -> {len(df)}")

    df = df.drop(columns=[c for c in DROP_SECONDARY_COLS if c in df.columns])

    flow_cols = [c for c in df.columns if c.startswith(FLOWMINDER_PREFIX)]
    df[flow_cols] = df[flow_cols].fillna(0)

    before = len(df)
    df = df.dropna()
    print(f"[Step 2.3] Final NaN cleanup: {before} -> {len(df)}")
    return df


def merge_rt_proxy(df: pd.DataFrame, rt: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(rt, on=["nom", "date"], how="left")
    df["rt_proxy_is_imputed"] = df["rt_proxy"].isna()
    df["rt_proxy"] = df["rt_proxy"].fillna(1.0)
    print(f"[Step 2.4] Merged Rt-proxy: {(~df['rt_proxy_is_imputed']).sum()}/{len(df)} real, rest imputed as neutral")
    return df


def prepare_final_table(rt: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(TRAINING_TABLE_PATH, parse_dates=["date"])
    df = trim_features(df)
    df = handle_missingness(df)
    df = merge_rt_proxy(df, rt)
    df.to_csv(FINAL_TABLE_PATH, index=False)
    print(f"[Step 2] Saved: {FINAL_TABLE_PATH}  shape={df.shape}  any NaN? {df.isna().any().any()}")
    return df


# ---------------------------------------------------------------------
# Step 3: One-Class SVM
# ---------------------------------------------------------------------

def fit_svm(df: pd.DataFrame):
    for col in RATE_SOURCE_COLS:
        df[f"{col}_rate"] = df[col] / df["pop_count"] * 100_000

    train = df[df["date"] < SPLIT_DATE].copy()
    test = df[df["date"] >= SPLIT_DATE].copy()
    print(f"\n[Step 3] Temporal split at {SPLIT_DATE}: train={len(train)}, test={len(test)}")

    scaler = StandardScaler()
    X_train = scaler.fit_transform(train[FEATURE_COLS])
    X_test = scaler.transform(test[FEATURE_COLS])

    model = OneClassSVM(kernel="rbf", nu=SVM_NU, gamma=SVM_GAMMA)
    model.fit(X_train)

    train_pred, test_pred = model.predict(X_train), model.predict(X_test)
    train_scores, test_scores = model.decision_function(X_train), model.decision_function(X_test)

    print(f"Train: {sum(train_pred == -1)}/{len(train_pred)} flagged")
    print(f"Test:  {sum(test_pred == -1)}/{len(test_pred)} flagged")

    train = train.assign(prediction=train_pred, anomaly_score=train_scores, split="train")
    test = test.assign(prediction=test_pred, anomaly_score=test_scores, split="test")
    result = pd.concat([train, test]).sort_values(["date", "nom"])
    result.to_csv(SVM_OUT_PATH, index=False)
    print(f"Saved: {SVM_OUT_PATH}")

    flagged_test = test[test["prediction"] == -1].sort_values("anomaly_score")
    print("\n=== flagged anomalies (test set) ===")
    print(flagged_test[["nom", "date", "new_suspected_cases", "new_suspected_cases_rate",
                         "min_minutes_to_active_zone", "anomaly_score"]].to_string(index=False))


def main():
    rt = compute_rt_proxy()
    df = prepare_final_table(rt)
    fit_svm(df)


if __name__ == "__main__":
    main()