import os
import csv
import glob
import hashlib
import re
from io import StringIO
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from data_processing import clean_dataframe, process_shapefile, join_insp_sitrep_csvs

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


def psql_insert_copy(table, conn, keys, data_iter):
    """
    Super-fast PostgreSQL COPY stream handler.
    Bypasses INSERT statements and uploads directly via an in-memory CSV buffer.
    """
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)

        columns = ', '.join(f'"{k}"' for k in keys)
        if table.schema:
            table_name = f"{table.schema}.{table.name}"
        else:
            table_name = table.name

        sql = f"COPY {table_name} ({columns}) FROM STDIN WITH CSV FREEZE"
        cur.copy_expert(sql=sql, file=s_buf)


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

    # --- 2. Zero-Loss Merge of individual INSP sitreps into a single wide CSV ---
    data_test_dir = Path("data_test")
    merged_output_path = data_test_dir / "insp_sitrep_merged.csv"
    
    try:
        print("🔗 Merging all individual INSP sitrep CSVs into a single wide table...")
        join_insp_sitrep_csvs(input_dir=data_test_dir, output_path=merged_output_path)
        print(f"✔ Wide table successfully compiled at {merged_output_path}")
    except Exception as e:
        print(f"⚠️ Merge failed: {e}. Individual sitreps will be processed raw instead.")

    # 3. Gather files inside data_test for DB sync
    all_files = glob.glob(os.path.join("data_test", "*"))
    processed_count = 0
    
    for file_path in all_files:
        filename = os.path.basename(file_path)
        name_lower = filename.lower()
        
        # Skip raw individual sitreps (we already merged them into 'insp_sitrep_merged.csv'!)
        if name_lower.startswith("insp_sitrep__") and name_lower != "insp_sitrep_merged.csv":
            continue
            
        # Flexible substring matching to ensure no file is skipped
        is_matched = (
            "insp" in name_lower or
            "epi_cases" in name_lower or
            "worldpop" in name_lower or
            "osrm" in name_lower or
            "cross_border" in name_lower or
            "flowminder" in name_lower or
            "grid3" in name_lower or
            name_lower.endswith(".shp")
        )
        
        if not is_matched:
            continue
            
        # Format clean, SQL-friendly table names
        clean_name = (filename.lower()
                      .replace(".matrix.csv", "_matrix")
                      .replace(".csv", "")
                      .replace(".shp", "_shapefile")
                      .replace("__", "_")
                      .replace(".", "_")
                      .replace("-", "_"))
        
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        
        # PostgreSQL safety: Truncate table names if they exceed 60 characters
        if len(clean_name) > 60:
            name_hash = hashlib.md5(clean_name.encode('utf-8')).hexdigest()[:6]
            clean_name = f"{clean_name[:50]}_{name_hash}"
        
        # Skip helper shapefile extensions
        if any(name_lower.endswith(ext) for ext in [".shx", ".dbf", ".prj", ".cpg"]):
            continue

        print(f"📦 Re-building Table: '{clean_name}' from raw file...")
        
        try:
            if name_lower.endswith(".shp"):
                processed_df = process_shapefile(file_path)
            else:
                raw_df = pd.read_csv(file_path)
                processed_df = clean_dataframe(raw_df)
            
            # Standardize headers to lower_snake_case
            processed_df.columns = [clean_column_name(col) for col in processed_df.columns]
            
            # Save normal table to database using optimized psql bulk COPY
            print(f"🚀 Streaming {len(processed_df)} rows to '{clean_name}' using fast COPY...")
            
            if DATABASE_URL:
                # Use lightning-fast COPY for PostgreSQL
                processed_df.to_sql(
                    clean_name, 
                    engine, 
                    if_exists='replace', 
                    index=False,
                    method=psql_insert_copy
                )
            else:
                # Fallback for local SQLite tests
                processed_df.to_sql(
                    clean_name, 
                    engine, 
                    if_exists='replace', 
                    index=False
                )
                
            print(f"✔ Table '{clean_name}' completely replaced.")
            processed_count += 1
            
        except Exception as e:
            print(f"❌ Failed to process '{filename}': {e}")
            
    print(f"🎉 Complete! All previous tables cleared; {processed_count} tables deployed successfully.")

if __name__ == "__main__":
    clean_and_sync()
