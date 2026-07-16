import os
import glob
import hashlib
import re
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

from data_processing import (
    clean_dataframe, 
    join_insp_sitrep_csvs, 
    join_flowminder_csvs, 
    join_worldpop_csvs, 
    force_nom_first,
    compute_osrm_nearest_active
)

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
    print("🔌 Connected successfully to your Cloud database!")
else:
    engine = create_engine("sqlite:///viralwatch.db")
    print("📁 DATABASE_URL not found. Saving locally to viralwatch.db.")


def clean_column_name(col):
    c = col.lower().strip()
    c = re.sub(r'[^a-z0-9_]', '_', c)
    c = re.sub(r'_+', '_', c)
    return c.strip('_')


def clean_and_sync():
    print("🔥 Starting database sync cycle...")
    
    if DATABASE_URL:
        try:
            with engine.begin() as conn:
                print("🧹 Dropping and recreating public schema...")
                conn.execute(text("DROP SCHEMA public CASCADE;"))
                conn.execute(text("CREATE SCHEMA public;"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        except Exception as e:
            print(f"⚠️ Schema reset warning: {e}")

    # Set up our system-relative paths
    REPO_ROOT = Path(__file__).resolve().parent.parent
    
    # Paths required for your special OSRM script
    OSRM_PATH = REPO_ROOT / "data/external/BDBV2026-Data/build/long/osrm__travel_time.csv"
    ALIASES_PATH = REPO_ROOT / "data/external/BDBV2026-Data/data/aliases.csv"
    SITREP_PATH = REPO_ROOT / "output/insp_sitrep_training_window.csv"
    OUT_PATH = REPO_ROOT / "output/osrm_nearest_active_feature.csv"

    # Default general data directory mapping
    data_dir = Path("data_test")
    if not data_dir.exists() or not any(data_dir.iterdir()):
        data_dir = Path(".")

    # --- 1. Custom OSRM Calculation Feature Generation & Upload ---
    try:
        if OSRM_PATH.exists() and SITREP_PATH.exists():
            print("🗺️ Running custom OSRM nearest active-zone calculation...")
            osrm_df = compute_osrm_nearest_active(OSRM_PATH, ALIASES_PATH, SITREP_PATH, OUT_PATH)
            
            # Post-Process for Database Injection (Force 'nom' First)
            osrm_df = clean_dataframe(osrm_df)
            osrm_df.columns = [clean_column_name(col) for col in osrm_df.columns]
            osrm_df = force_nom_first(osrm_df)
            
            print(f"📋 'osrm_nearest_active_feature' columns right before SQL: {list(osrm_df.columns)}")
            osrm_df.to_sql("osrm_nearest_active_feature", engine, if_exists='replace', index=False)
            print("✔ Custom table 'osrm_nearest_active_feature' successfully saved in DB!")
        else:
            print(f"⚠️ OSRM Source File or Sitrep Training Window not found. Skipping OSRM custom calculation.")
    except Exception as e:
        print(f"❌ OSRM feature calculation or upload failed: {e}")

    # --- 2. INSP Merge ---
    try:
        if len(list(data_dir.glob("insp_sitrep*.csv"))) > 0:
            merged_df = join_insp_sitrep_csvs(input_dir=data_dir, output_path=data_dir / "insp_sitrep_merged.csv")
            merged_df = clean_dataframe(merged_df)
            merged_df.columns = [clean_column_name(col) for col in merged_df.columns]
            merged_df = force_nom_first(merged_df)
            
            print(f"📋 'insp_sitrep_merged' columns right before SQL: {list(merged_df.columns)}")
            merged_df.to_sql("insp_sitrep_merged", engine, if_exists='replace', index=False)
    except Exception as e:
        print(f"❌ INSP upload failed: {e}")

    # --- 3. Flowminder ---
    try:
        if len(list(data_dir.glob("flowminder*.csv"))) > 0:
            flow_df = join_flowminder_csvs(input_dir=data_dir, output_path=data_dir / "flowminder_merged.csv")
            flow_df = clean_dataframe(flow_df)
            flow_df.columns = [clean_column_name(col) for col in flow_df.columns]
            flow_df = force_nom_first(flow_df)
            
            print(f"📋 'flowminder_merged' columns right before SQL: {list(flow_df.columns)}")
            flow_df.to_sql("flowminder_merged", engine, if_exists='replace', index=False)
    except Exception as e:
        print(f"❌ Flowminder upload failed: {e}")

    # --- 4. WorldPop ---
    try:
        if len(list(data_dir.glob("*worldpop*.csv"))) > 0:
            wp_df = join_worldpop_csvs(input_dir=data_dir, output_path=data_dir / "worldpop_merged.csv")
            wp_df = clean_dataframe(wp_df)
            wp_df.columns = [clean_column_name(col) for col in wp_df.columns]
            wp_df = force_nom_first(wp_df)
            
            print(f"📋 'worldpop_merged' columns right before SQL: {list(wp_df.columns)}")
            wp_df.to_sql("worldpop_merged", engine, if_exists='replace', index=False)
    except Exception as e:
        print(f"❌ WorldPop upload failed: {e}")

    # --- 5. Remaining files (Skipping RAW OSRM files completely!) ---
    all_files = glob.glob(os.path.join(str(data_dir), "*"))
    for file_path in all_files:
        filename = os.path.basename(file_path)
        name_lower = filename.lower()
        
        # Completely skip raw/processed INSP, Flowminder, WorldPop, AND ALL OSRM matrix tables
        if "insp_sitrep" in name_lower or "flowminder" in name_lower or "worldpop" in name_lower or "osrm" in name_lower:
            continue
            
        if not ("epi_cases" in name_lower):
            continue
            
        clean_name = (filename.lower().replace(".matrix.csv", "_matrix").replace(".csv", "").replace("-", "_"))
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')

        try:
            raw_df = pd.read_csv(file_path)
            processed_df = clean_dataframe(raw_df)
            processed_df.columns = [clean_column_name(col) for col in processed_df.columns]
            processed_df = force_nom_first(processed_df)
            
            print(f"📋 '{clean_name}' columns right before SQL: {list(processed_df.columns)}")
            processed_df.to_sql(clean_name, engine, if_exists='replace', index=False)
        except Exception as e:
            print(f"❌ Failed processing '{filename}': {e}")
            
    print("🎉 Sync completed successfully!")

if __name__ == "__main__":
    clean_and_sync()
