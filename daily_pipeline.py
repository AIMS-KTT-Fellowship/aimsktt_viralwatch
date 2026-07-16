import os
import glob
import hashlib
import re
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from data_processing import clean_dataframe, join_insp_sitrep_csvs

# 1. Fetch Connection String from Environment
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
    print("🔌 Connected successfully to your Cloud Aiven PostgreSQL database!")
else:
    engine = create_engine("sqlite:///data_test/viralwatch.db")
    print("📁 DATABASE_URL not found. Saving locally to data_test/viralwatch.db.")

def clean_column_name(col):
    """
    Standardizes column headers globally to lowercase separated by single underscores.
    """
    c = col.lower().strip()
    c = re.sub(r'[^a-z0-9_]', '_', c)
    c = re.sub(r'_+', '_', c)
    return c.strip('_')

def clean_and_sync():
    print("🔥 Starting complete database wipe-and-rebuild cycle...")
    
    if DATABASE_URL:
        try:
            with engine.begin() as conn:
                print("🧹 Dropping and recreating public schema...")
                conn.execute(text("DROP SCHEMA public CASCADE;"))
                conn.execute(text("CREATE SCHEMA public;"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
                print("✨ Schema successfully reset to empty!")
        except Exception as e:
            print(f"⚠️ Warning: Schema reset failed: {e}. Moving to standard table replacements.")

    # --- 2. Zero-Loss Merge of individual INSP sitreps directly into PostgreSQL ---
    data_test_dir = Path("data_test")
    merged_output_path = data_test_dir / "insp_sitrep_merged.csv"
    
    try:
        print("🔗 Merging all individual INSP sitrep CSVs into a single wide table...")
        # Create output parent directory if it doesn't exist yet
        data_test_dir.mkdir(parents=True, exist_ok=True)
        
        merged_df = join_insp_sitrep_csvs(input_dir=data_test_dir, output_path=merged_output_path)
        print(f"✔ Wide table successfully compiled locally at {merged_output_path}")
        
        # Clean columns and insert directly here! No relying on file loop!
        print("🚀 Uploading 'insp_sitrep_merged' directly to DB...")
        merged_df = clean_dataframe(merged_df)
        merged_df.columns = [clean_column_name(col) for col in merged_df.columns]
        
        merged_df.to_sql(
            "insp_sitrep_merged", 
            engine, 
            if_exists='replace', 
            index=False,
            method='multi',
            chunksize=5000
        )
        print("✔ Table 'insp_sitrep_merged' successfully written to Database!")
        
    except Exception as e:
        print(f"❌ Critical Merge / Upload failed: {e}")

    # 3. Gather files inside data_test for standard DB sync (skipping any raw/processed INSP files)
    all_files = glob.glob(os.path.join("data_test", "*"))
    processed_count = 1  # Starting at 1 because we already did the merged table
    
    for file_path in all_files:
        filename = os.path.basename(file_path)
        name_lower = filename.lower()
        
        # Skip ALL individual raw sitrep files as well as the merged file (already processed!)
        if "insp" in name_lower:
            continue
            
        # Skip all shapefiles and spatial helper files completely
        if any(name_lower.endswith(ext) for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]):
            continue
            
        # Flexible substring matching to ensure target CSVs are processed
        is_matched = (
            "epi_cases" in name_lower or
            "worldpop" in name_lower or
            "osrm" in name_lower or
            "cross_border" in name_lower or
            "flowminder" in name_lower or
            "grid3" in name_lower
        )
        
        if not is_matched:
            continue
            
        # Format clean, SQL-friendly table names
        clean_name = (filename.lower()
                      .replace(".matrix.csv", "_matrix")
                      .replace(".csv", "")
                      .replace("__", "_")
                      .replace(".", "_")
                      .replace("-", "_"))
        
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        
        # PostgreSQL safety: Truncate table names if they exceed 60 characters
        if len(clean_name) > 60:
            name_hash = hashlib.md5(clean_name.encode('utf-8')).hexdigest()[:6]
            clean_name = f"{clean_name[:50]}_{name_hash}"

        print(f"📦 Re-building Table: '{clean_name}' from raw file...")
        
        try:
            raw_df = pd.read_csv(file_path)
            processed_df = clean_dataframe(raw_df)
            
            # Standardize headers to lower_snake_case
            processed_df.columns = [clean_column_name(col) for col in processed_df.columns]
            
            # Save normal table to database using optimized batched inserting
            print(f"🚀 Uploading {len(processed_df)} rows to '{clean_name}'...")
            processed_df.to_sql(
                clean_name, 
                engine, 
                if_exists='replace', 
                index=False,
                method='multi',
                chunksize=5000
            )
            print(f"✔ Table '{clean_name}' completely replaced.")
            processed_count += 1
            
        except Exception as e:
            print(f"❌ Failed to process '{filename}': {e}")
            
    print(f"🎉 Complete! All previous tables cleared; {processed_count} tables deployed successfully.")

if __name__ == "__main__":
    clean_and_sync()
