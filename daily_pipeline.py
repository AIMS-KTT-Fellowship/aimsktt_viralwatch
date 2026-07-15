import os
import glob
import pandas as pd
from sqlalchemy import create_engine
from data_processing import clean_dataframe, process_shapefile

# 1. Fetch Aiven Connection String from Environment
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
    print("🔌 Connected successfully to your Cloud Aiven PostgreSQL database!")
else:
    engine = create_engine("sqlite:///data_test/viralwatch.db")
    print("📁 DATABASE_URL not found. Saving locally to data_test/viralwatch.db.")

def clean_and_sync():
    print("🚀 Running custom build and shapefile ingestion pipeline...")
    
    # Gather everything saved inside data_test
    all_files = glob.glob(os.path.join("data_test", "*"))
    
    processed_count = 0
    
    for file_path in all_files:
        filename = os.path.basename(file_path)
        name_lower = filename.lower()
        
        # Define target matching criteria matching user lists
        is_matched = (
            name_lower.startswith("insp") or
            name_lower.startswith("epi_cases") or
            name_lower.startswith("worldpop_") or
            name_lower.startswith("osrm_") or
            name_lower.startswith("cross_border") or
            name_lower.startswith("flowminder_short") or
            name_lower.startswith("grid3_healthsites") or
            name_lower.endswith(".shp")
        )
        
        if not is_matched:
            continue
            
        # Determine table name
        clean_name = (filename.lower()
                      .replace(".matrix.csv", "_matrix")
                      .replace(".csv", "")
                      .replace(".shp", "_shapefile")
                      .replace("__", "_")
                      .replace(".", "_")
                      .replace("-", "_"))
        
        # Skip support files for shapefiles (e.g. .shx, .dbf) since the .shp processor consumes them
        if any(name_lower.endswith(ext) for ext in [".shx", ".dbf", ".prj", ".cpg"]):
            continue

        print(f"📦 Processing: '{filename}' -> DB Table: '{clean_name}'")
        
        try:
            # Route processing based on file type
            if name_lower.endswith(".shp"):
                processed_df = process_shapefile(file_path)
            else:
                raw_df = pd.read_csv(file_path)
                processed_df = clean_dataframe(raw_df)
            
            # Save to database
            processed_df.to_sql(clean_name, engine, if_exists='replace', index=False)
            print(f"✔ Table '{clean_name}' successfully built and sync'd.")
            processed_count += 1
            
        except Exception as e:
            print(f"❌ Failed to process '{filename}': {e}")
            
    print(f"🎉 Complete! {processed_count} targeted tables written to the database.")

if __name__ == "__main__":
    clean_and_sync()
