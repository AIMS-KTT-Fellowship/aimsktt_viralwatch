import os
import re
import json
from pathlib import Path
import pandas as pd
import numpy as np
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

# Safe imports for NLP module to prevent startup import crashes
try:
    from nlp_processing import run_nlp_pipeline
except Exception as import_err:
    print(f"⚠️ Warning: Could not cleanly import NLP processing modules on startup. Details: {import_err}")
    run_nlp_pipeline = None

# --- Database Engine Setup (Aiven Postgres Compatible) ---
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    if "sslmode=" not in DATABASE_URL:
        separator = "&" if "?" in DATABASE_URL else "?"
        DATABASE_URL += f"{separator}sslmode=require"
        
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine("sqlite:///viralwatch.db")

# --- Local Paths ---
DATA_REPO_DIR = Path("BDBV2026-Data")
BUILD_DIR = DATA_REPO_DIR / "build"
BUILD_LONG_DIR = DATA_REPO_DIR / "build" / "long"

OSRM_PATH = BUILD_DIR / "matrix" / "osrm__travel_time__static.matrix.csv"
ALIASES_PATH = DATA_REPO_DIR / "data" / "aliases.csv"
WP_COUNT_PATH = BUILD_LONG_DIR / "worldpop__pop_count.csv"
WP_DENSITY_PATH = BUILD_LONG_DIR / "worldpop__pop_density.csv"


def clean_column_name(col):
    """Sanitizes columns to safe, standardized database snake_case."""
    c = str(col).lower().strip()
    c = re.sub(r'[^a-z0-9_]', '_', c)
    c = re.sub(r'_+', '_', c)
    return c.strip('_')


def generate_fallback_forecasts(final_table_path):
    """Generates a baseline 7-day rolling forecast when train_model is missing."""
    print("⚠️ 'train_model' module not found. Running baseline fallback forecast...")
    df = pd.read_csv(final_table_path)
    case_cols = [c for c in df.columns if any(x in c.lower() for x in ['case', 'cas', 'active'])]
    
    predictions = []
    for hz, group in df.groupby('nom'):
        group_sorted = group.sort_values(by='date')
        if not group_sorted.empty:
            last_row = group_sorted.iloc[-1]
            last_date = pd.to_datetime(last_row['date'])
            
            last_val = 0
            if case_cols:
                last_val = last_row[case_cols].mean()
                if pd.isna(last_val):
                    last_val = 0
            
            for i in range(1, 8):
                pred_date = last_date + pd.Timedelta(days=i)
                predictions.append({
                    "health_zone": hz,
                    "date": pred_date.date(),
                    "predicted_cases": max(0.0, float(last_val))
                })
                
    return pd.DataFrame(predictions)


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
        
        raw_table_path = output_dir / "training_table.csv"
        df_raw = create_training_table(sit_p, osrm_p, flow_p, wp_p, raw_table_path)
        
        df_trimmed = trim_features(df_raw)
        df_final = handle_missingness(df_trimmed)
        
        final_table_path = output_dir / "training_table_final.csv"
        df_final = df_final[["nom", "date"] + [c for c in df_final.columns if c not in ["nom", "date"]]]
        df_final.to_csv(final_table_path, index=False)

        raw_db = clean_dataframe(df_raw.copy())
        raw_db.columns = [clean_column_name(c) for c in raw_db.columns]
        
        db_cols_raw = ["health_zone", "date"] + [c for c in raw_db.columns if c not in ["health_zone", "date"]]
        raw_db = raw_db[db_cols_raw]

        final_db = clean_dataframe(df_final.copy())
        final_db.columns = [clean_column_name(c) for c in final_db.columns]
        
        db_cols_final = ["health_zone", "date"] + [c for c in final_db.columns if c not in ["health_zone", "date"]]
        final_db = final_db[db_cols_final]
        
        raw_table_name = "training_table_raw"
        final_table_name = "training_table_final"

        with engine.begin() as conn:
            inspector = inspect(engine)
            
            # --- 1. Handle Raw Table ---
            if inspector.has_table(raw_table_name):
                db_columns = [col['name'] for col in inspector.get_columns(raw_table_name)]
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
                db_columns = [col['name'] for col in inspector.get_columns(final_table_name)]
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

    # --- 6. Generate Model Data Table ---
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

        raw_sitrep_filepath = output_dir / "insp_sitrep_training_window.csv"
        pop_filepath = BUILD_LONG_DIR / "worldpop__pop_density.csv"
        matrix_filepath = OSRM_PATH  
        
        print("   -> Calculating days since initial case benchmark...")
        raw_cases = pd.read_csv(raw_sitrep_filepath, header=None)
        df_days = calculate_days_since_first_case(raw_cases)
        
        print("   -> Parsing spatial density distributions...")
        df_pop_density = load_population_density(pop_filepath)
        
        print("   -> Evaluating travel metrics relative to Bunia epicenter...")
        df_travel_time = extract_distance_to_epicenter(matrix_filepath, epicenter_name="Bunia")
        
        df_travel_time['travel_time_to_epicenter'] = pd.to_numeric(df_travel_time['travel_time_to_epicenter'], errors='coerce')
        df_travel_time.loc[df_travel_time['travel_time_to_epicenter'] < 0, 'travel_time_to_epicenter'] = np.nan
        travel_median = df_travel_time['travel_time_to_epicenter'].dropna().median() if not df_travel_time['travel_time_to_epicenter'].dropna().empty else 0
        df_travel_time['travel_time_to_epicenter'] = df_travel_time['travel_time_to_epicenter'].fillna(travel_median)
        
        print("   -> Assembling master model compilation...")
        df_master = assemble_model_data(df_days, df_pop_density, df_travel_time)
        df_target_features = create_target_variable(df_master)

        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        cols_to_keep = []
        for col in df_target_features.columns:
            col_str = str(col)
            if col in ["nom", "date"]:
                cols_to_keep.append(col)
            elif not (col_str.isdigit() or isinstance(col, int) or date_pattern.match(col_str)):
                cols_to_keep.append(col)

        df_target_features = df_target_features[cols_to_keep]

        ml_local_backup = output_dir / "model_data_final.csv"
        df_target_features.to_csv(ml_local_backup, index=False)

        model_db = df_target_features.copy()
        model_db.columns = [clean_column_name(c) for c in model_db.columns]
        
        db_cols_model = ["health_zone", "date"] + [c for c in model_db.columns if c not in ["health_zone", "date"]]
        model_db = model_db[db_cols_model]

        with engine.begin() as conn:
            print(f"🔄 Dropping and rebuilding `{model_table_name}` schema...")
            conn.exec_driver_sql(f"DROP TABLE IF EXISTS {model_table_name} CASCADE;")

            print(f"📥 Exporting structured features to `{model_table_name}`...")
            model_db.to_sql(
                name=model_table_name,
                con=conn,
                if_exists="replace",
                index=False
            )
            
        print(f"💾 Successfully processed and populated `{model_table_name}` inside Database!")
        
    except Exception as e:
        print(f"❌ Failed to construct or ingest features into `{model_table_name}`: {e}")

    # --- 7. Run ML Model and Upload Predictions ---
    print("\n⏳ Running Machine Learning Model training & forecasting...")
    try:
        try:
            from train_model import generate_forecasts
            print("🚀 'train_model' module loaded successfully. Commencing forecast computation...")
            predictions_df = generate_forecasts(final_table_path)
        except ModuleNotFoundError:
            predictions_df = generate_fallback_forecasts(final_table_path)
        
        predictions_df.columns = [clean_column_name(c) for c in predictions_df.columns]
        predictions_db = predictions_df[["health_zone", "date", "predicted_cases"]].copy()
        predictions_db["date"] = pd.to_datetime(predictions_db["date"]).dt.date
        
        prediction_table_name = "model_predictions"

        with engine.begin() as conn:
            inspector = inspect(engine)
            if inspector.has_table(prediction_table_name):
                print(f"🧹 Table `{prediction_table_name}` exists. Truncating rows...")
                conn.exec_driver_sql(f"TRUNCATE TABLE {prediction_table_name};")
                if_exists_pred = "append"
            else:
                print(f"🆕 Table `{prediction_table_name}` does not exist. Creating it...")
                if_exists_pred = "replace"
                
            print(f"📥 Appending new prediction records to `{prediction_table_name}`...")
            predictions_db.to_sql(
                name=prediction_table_name,
                con=conn,
                if_exists=if_exists_pred,
                index=False
            )
            
        print(f"💾 Successfully logged model predictions to `{prediction_table_name}`!")

    except Exception as e:
        print(f"❌ Model training or prediction upload failed: {e}")

    # --- 8. RUN CONSOLIDATED NLP ENGINE & LOG TO DATABASE (TIME-CONSUMING LAST STEP) ---[cite: 3, 4, 5, 6]
    print("\n⏳ [FINAL STAGE] Launching Long-Running NLP Processing Engine...")
    nlp_table_name = "nlp_result"
    
    if run_nlp_pipeline is None:
        print("❌ Skip Warning: Skipping Step 8 because NLP modules failed to import on initialization.")
        return

    try:
        nlp_df = run_nlp_pipeline()
        
        if nlp_df is not None and not nlp_df.empty:
            print("📥 Uploading processed NLP elements into relational database schema...")
            nlp_db_ready = nlp_df.copy()
            nlp_db_ready.columns = [clean_column_name(c) for c in nlp_db_ready.columns]
            
            if "health_zone" in nlp_db_ready.columns and "date" in nlp_db_ready.columns:
                nlp_cols_ordered = ["health_zone", "date"] + [c for c in nlp_db_ready.columns if c not in ["health_zone", "date"]]
                nlp_db_ready = nlp_db_ready[nlp_cols_ordered]
            
            with engine.begin() as conn:
                print(f"🔄 Rebuilding system table `{nlp_table_name}`...")
                conn.exec_driver_sql(f"DROP TABLE IF EXISTS {nlp_table_name} CASCADE;")
                
                nlp_db_ready.to_sql(
                    name=nlp_table_name,
                    con=conn,
                    if_exists="replace",
                    index=False
                )
            print(f"💾 Table `{nlp_table_name}` safely logged inside Postgres Database backend!")
        else:
            print("⚠️ NLP processing yielded zero valid updates for pipeline conversion.")
            
        print("\n🎉 Entire pipeline execution completed from raw ingest to analytical DB predictions!")
        
    except Exception as e:
         print(f"❌ Critical Error occurred inside Stage 8 NLP pipeline routines: {e}")


if __name__ == "__main__":
    run_pipeline()
