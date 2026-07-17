import os
import re
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

from data_processing import (
    clean_dataframe,
    join_insp_sitrep_csvs,
    join_flowminder_csvs,
    compute_osrm_nearest_active,
    clean_and_merge_flowminder,
    merge_worldpop,
    create_training_table,
    trim_features,
    handle_missingness
)

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine("sqlite:///viralwatch.db")


# --- Local Paths ---
DATA_REPO_DIR = Path("BDBV2026-Data")
BUILD_LONG_DIR = DATA_REPO_DIR / "build" / "long"
BUILD_DIR = DATA_REPO_DIR / "build"

# Source configurations
OSRM_PATH = BUILD_LONG_DIR / "osrm__travel_time.csv"
ALIASES_PATH = DATA_REPO_DIR / "data" / "aliases.csv"
WP_COUNT_PATH = BUILD_LONG_DIR / "worldpop__pop_count.csv"
WP_DENSITY_PATH = BUILD_LONG_DIR / "worldpop__pop_density.csv"


def clean_column_name(col):
    c = col.lower().strip()
    c = re.sub(r'[^a-z0-9_]', '_', c)
    c = re.sub(r'_+', '_', c)
    return c.strip('_')


def run_pipeline():
    workspace_root = Path(".").resolve()
    output_dir = workspace_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Compile INSP Sitreps ---
    print("⏳ Compiling INSP Sitreps...")
    try:
        merged_sitrep_path = output_dir / "insp_sitrep_merged.csv"
        raw_sitrep = join_insp_sitrep_csvs(BUILD_LONG_DIR, merged_sitrep_path)
        
        for col in raw_sitrep.columns:
            if col not in ["nom", "date"]:
                raw_sitrep[col] = raw_sitrep[col].replace("ND", pd.NA)
                raw_sitrep[col] = pd.to_numeric(raw_sitrep[col], errors="coerce")

        zone_rows = raw_sitrep[raw_sitrep["nom"].notna()].copy()
        zone_rows = zone_rows[zone_rows["date"].notna()].copy()
        zone_rows.to_csv(output_dir / "insp_sitrep_zone_level_clean.csv", index=False)

        training_df = zone_rows[(zone_rows["date"] >= "2026-05-14") & (zone_rows["date"] <= "2026-05-29")].copy()
        training_df.to_csv(output_dir / "insp_sitrep_training_window.csv", index=False)
        print("✅ INSP Sitrep compilation completed.")
    except Exception as e:
        print(f"❌ INSP Sitrep failed: {e}")

    # --- 2. Calculate OSRM Nearest Active ---
    print("⏳ Processing travel matrices...")
    try:
        sitrep_path = output_dir / "insp_sitrep_training_window.csv"
        out_osrm_path = output_dir / "osrm_nearest_active_feature.csv"
        
        if sitrep_path.exists():
            compute_osrm_nearest_active(OSRM_PATH, ALIASES_PATH, sitrep_path, out_osrm_path)
            print("✅ Travel metrics compiled.")
    except Exception as e:
        print(f"❌ Travel metric calculation failed: {e}")

    # --- 3. Clean and Merge Flowminder ---
    print("⏳ Processing Flowminder data...")
    try:
        merged_flowminder_path = output_dir / "flowminder_merged.csv"
        join_flowminder_csvs(BUILD_LONG_DIR, merged_flowminder_path)
        clean_and_merge_flowminder(merged_flowminder_path, output_dir / "flowminder_clean.csv")
        print("✅ Flowminder pipeline finished.")
    except Exception as e:
        print(f"❌ Flowminder pipeline failed: {e}")

    # --- 4. Merge WorldPop ---
    print("⏳ Merging WorldPop parameters...")
    try:
        merge_worldpop(WP_COUNT_PATH, WP_DENSITY_PATH, output_dir / "worldpop_merged.csv")
        print("✅ WorldPop configuration finished.")
    except Exception as e:
        print(f"❌ WorldPop merging failed: {e}")

    # --- 5. Generate and Clean ML-Ready Training Table ---
    print("\n⏳ Building training datasets...")
    try:
        sit_p = output_dir / "insp_sitrep_training_window.csv"
        osrm_p = output_dir / "osrm_nearest_active_feature.csv"
        flow_p = output_dir / "flowminder_clean.csv"
        wp_p = output_dir / "worldpop_merged.csv"
        
        # A. Join features in memory (no 'raw' table written to DB)[cite: 7]
        raw_table_path = output_dir / "training_table.csv"
        df_raw = create_training_table(sit_p, osrm_p, flow_p, wp_p, raw_table_path)
        
        # B. Apply feature trimming and missingness handling[cite: 6]
        df_trimmed = trim_features(df_raw)
        df_final = handle_missingness(df_trimmed)
        
        # Save local final output backup
        final_table_path = output_dir / "training_table_final.csv"
        df_final.to_csv(final_table_path, index=False)

        # Prepare DataFrame for SQL ingestion
        final_db = clean_dataframe(df_final.copy())
        final_db.columns = [clean_column_name(c) for c in final_db.columns]
        
        target_table_name = "training_table_final"

        # C. Secure DB Upload (TRUNCATE & APPEND ONLY)
        with engine.begin() as conn:
            print(f"🧹 Truncating existing rows in `{target_table_name}`...")
            conn.exec_driver_sql(f"TRUNCATE TABLE {target_table_name};")
            
            print(f"📥 Appending new clean data to `{target_table_name}`...")
            final_db.to_sql(
                name=target_table_name,
                con=conn,
                if_exists="append",
                index=False
            )
            
        print(f"💾 Successfully refreshed data in `{target_table_name}`!")
        print(f"✅ Success! Active training window contains {len(df_final)} validated data points.")

    except Exception as e:
        print(f"❌ Generating training data outputs failed: {e}")


if __name__ == "__main__":
    run_pipeline()
