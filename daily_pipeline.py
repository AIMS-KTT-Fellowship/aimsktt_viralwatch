import os
import re
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text, inspect

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

# --- Database Engine Setup (Aiven Postgres Compatible) ---
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # Aiven URIs starting with "postgres://" are converted to "postgresql://" for SQLAlchemy
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Force Aiven's mandatory "sslmode=require" configuration if not present
    if "sslmode=" not in DATABASE_URL:
        separator = "&" if "?" in DATABASE_URL else "?"
        DATABASE_URL += f"{separator}sslmode=require"
        
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
    """Sanitizes columns to safe, standardized database snake_case."""
    c = str(col).lower().strip()
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

    # --- 5. Generate and Clean ML-Ready Training Tables ---
    print("\n⏳ Building training datasets...")
    try:
        sit_p = output_dir / "insp_sitrep_training_window.csv"
        osrm_p = output_dir / "osrm_nearest_active_feature.csv"
        flow_p = output_dir / "flowminder_clean.csv"
        wp_p = output_dir / "worldpop_merged.csv"
        
        # A. Join features in memory (CSVs will already have "nom" and "date" first)
        raw_table_path = output_dir / "training_table.csv"
        df_raw = create_training_table(sit_p, osrm_p, flow_p, wp_p, raw_table_path)
        
        # B. Apply feature trimming and missingness handling
        df_trimmed = trim_features(df_raw)
        df_final = handle_missingness(df_trimmed)
        
        # Ensure final CSV has "nom" and "date" first
        final_table_path = output_dir / "training_table_final.csv"
        df_final = df_final[["nom", "date"] + [c for c in df_final.columns if c not in ["nom", "date"]]]
        df_final.to_csv(final_table_path, index=False)

        # Prepare Raw DataFrame for SQL ingestion
        raw_db = clean_dataframe(df_raw.copy())
        raw_db.columns = [clean_column_name(c) for c in raw_db.columns]
        
        # Force "health_zone" first, "date" second
        db_cols_raw = ["health_zone", "date"] + [c for c in raw_db.columns if c not in ["health_zone", "date"]]
        raw_db = raw_db[db_cols_raw]

        # Prepare Final DataFrame for SQL ingestion
        final_db = clean_dataframe(df_final.copy())
        final_db.columns = [clean_column_name(c) for c in final_db.columns]
        
        # Force "health_zone" first, "date" second
        db_cols_final = ["health_zone", "date"] + [c for c in final_db.columns if c not in ["health_zone", "date"]]
        final_db = final_db[db_cols_final]
        
        raw_table_name = "training_table_raw"
        final_table_name = "training_table_final"

        # C. Secure DB Upload (FORCE EXACT COLUMN ORDER USING DROP & REPLACE)
        with engine.begin() as conn:
            inspector = inspect(engine)
            
            # --- 1. Handle Raw Table ---
            if inspector.has_table(raw_table_name):
                # Retrieve the current database column order
                db_columns = [col['name'] for col in inspector.get_columns(raw_table_name)]
                # Check if "health_zone" and "date" are already the first two columns
                if db_columns[:2] == ["health_zone", "date"]:
                    print(f"🧹 Table `{raw_table_name}` has correct column order. Truncating rows...")
                    conn.exec_driver_sql(f"TRUNCATE TABLE {raw_table_name};")
                    if_exists_raw = "append"
                else:
                    print(f"🔄 Column order mismatch in `{raw_table_name}`. Dropping and recreating table...")
                    conn.exec_driver_sql(f"DROP TABLE IF EXISTS {raw_table_name} CASCADE;")
                    if_exists_raw = "replace"
            else:
                print(f"🆕 `{raw_table_name}` does not exist. Creating it fresh...")
                if_exists_raw = "replace"

            print(f"📥 Loading data into `{raw_table_name}`...")
            raw_db.to_sql(
                name=raw_table_name,
                con=conn,
                if_exists=if_exists_raw,
                index=False
            )

            # --- 2. Handle Final Table ---
            if inspector.has_table(final_table_name):
                # Retrieve the current database column order
                db_columns = [col['name'] for col in inspector.get_columns(final_table_name)]
                # Check if "health_zone" and "date" are already the first two columns
                if db_columns[:2] == ["health_zone", "date"]:
                    print(f"🧹 Table `{final_table_name}` has correct column order. Truncating rows...")
                    conn.exec_driver_sql(f"TRUNCATE TABLE {final_table_name};")
                    if_exists_final = "append"
                else:
                    print(f"🔄 Column order mismatch in `{final_table_name}`. Dropping and recreating table...")
                    conn.exec_driver_sql(f"DROP TABLE IF EXISTS {final_table_name} CASCADE;")
                    if_exists_final = "replace"
            else:
                print(f"🆕 `{final_table_name}` does not exist. Creating it fresh...")
                if_exists_final = "replace"

            print(f"📥 Loading clean data into `{final_table_name}`...")
            final_db.to_sql(
                name=final_table_name,
                con=conn,
                if_exists=if_exists_final,
                index=False
            )
            
        print(f"💾 Successfully synchronized training tables inside the Postgres Database!")

    except Exception as e:
        print(f"❌ Generating training data outputs failed: {e}")

    # --- 6. Generate Model Data Table (ML Outbreak Classification Features) ---
    print("\n⏳ Assembling ML features and classification target variables...")
    model_table_name = "model_data"
    try:
        from ml_data_processing import (
            calculate_days_since_first_case,
            load_population_density,
            extract_distance_to_epicenter,
            assemble_model_data,
            create_target_variable
        )

        # Dynamic inputs pointing to generated pipeline CSV pathways
        raw_sitrep_filepath = output_dir / "insp_sitrep_training_window.csv"
        pop_filepath = BUILD_LONG_DIR / "worldpop__pop_density.csv"
        matrix_filepath = BUILD_LONG_DIR / "osrm__travel_time.csv"
        
        # A. Execute Processing Flow
        print("   -> Calculating days since initial case benchmark...")
        raw_cases = pd.read_csv(raw_sitrep_filepath, header=None)
        df_days = calculate_days_since_first_case(raw_cases)
        
        print("   -> Parsing spatial density distributions...")
        df_pop_density = load_population_density(pop_filepath)
        
        print("   -> Evaluating travel metrics relative to Bunia epicenter...")
        df_travel_time = extract_distance_to_epicenter(matrix_filepath, epicenter_name="Bunia")
        
        print("   -> Assembling master model compilation...")
        df_master = assemble_model_data(df_days, df_pop_density, df_travel_time)
        df_target_features = create_target_variable(df_master)

        # Save a local CSV mirror backup
        ml_local_backup = output_dir / "model_data_final.csv"
        df_target_features.to_csv(ml_local_backup, index=False)

        # B. Prepare for DB Ingestion
        model_db = df_target_features.copy()
        model_db.columns = [clean_column_name(c) for c in model_db.columns]
        
        # Enforce designated column order: health_zone first, then date
        db_cols_model = ["health_zone", "date"] + [c for c in model_db.columns if c not in ["health_zone", "date"]]
        model_db = model_db[db_cols_model]

        # C. Secure DB Upload (Smart Check & Replace Schema)
        with engine.begin() as conn:
            inspector = inspect(engine)
            
            if inspector.has_table(model_table_name):
                db_columns = [col['name'] for col in inspector.get_columns(model_table_name)]
                if db_columns[:2] == ["health_zone", "date"]:
                    print(f"🧹 Table `{model_table_name}` schema matches. Truncating rows...")
                    conn.exec_driver_sql(f"TRUNCATE TABLE {model_table_name};")
                    if_exists_model = "append"
                else:
                    print(f"🔄 Schema mismatch in `{model_table_name}`. Dropping and rebuilding table...")
                    conn.exec_driver_sql(f"DROP TABLE IF EXISTS {model_table_name} CASCADE;")
                    if_exists_model = "replace"
            else:
                print(f"🆕 `{model_table_name}` table is missing. Recreating table fresh...")
                if_exists_model = "replace"

            print(f"📥 Exporting structured features to `{model_table_name}`...")
            model_db.to_sql(
                name=model_table_name,
                con=conn,
                if_exists=if_exists_model,
                index=False
            )
            
        print(f"💾 Successfully processed and populated `{model_table_name}` inside the Postgres Database!")
        
    except Exception as e:
        print(f"❌ Failed to construct or ingest features into `{model_table_name}`: {e}")

    # --- 7. Run ML Model and Upload Predictions ---
    print("\n⏳ Running Machine Learning Model training & forecasting...")
    try:
        # Import your model training function here (e.g., from train_model.py)
        # Assumes a function `generate_forecasts()` exists in `train_model.py`
        from train_model import generate_forecasts
        
        # 1. Generate predictions from the model
        predictions_df = generate_forecasts(final_table_path) 
        
        # 2. Standardize column schema names
        predictions_df.columns = [clean_column_name(c) for c in predictions_df.columns]
        
        # Expected structure: 'health_zone', 'date', 'predicted_cases'
        predictions_db = predictions_df[["health_zone", "date", "predicted_cases"]].copy()
        predictions_db["date"] = pd.to_datetime(predictions_db["date"]).dt.date
        
        prediction_table_name = "model_predictions"

        # 3. Securely append forecasts to the DB
        with engine.begin() as conn:
            print(f"📥 Appending new prediction records to `{prediction_table_name}`...")
            predictions_db.to_sql(
                name=prediction_table_name,
                con=conn,
                if_exists="append",
                index=False
            )
            
        print(f"💾 Successfully logged model predictions to `{prediction_table_name}`!")
        print("🎉 Entire pipeline execution completed from raw ingest to analytical DB predictions!")

    except Exception as e:
        print(f"❌ Model training or prediction upload failed: {e}")


if __name__ == "__main__":
    run_pipeline()
