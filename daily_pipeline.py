import os
import glob
import hashlib
import pandas as pd
from sqlalchemy import create_engine, text
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

    # Gather everything saved inside data_test
    all_files = glob.glob(os.path.join("data_test", "*"))
    processed_count = 0
    
    # Dictionary structures to store WorldPop dataframes temporarily
    worldpop_dfs = {"count": None, "density": None}
    
    for file_path in all_files:
        filename = os.path.basename(file_path)
        name_lower = filename.lower()
        
        # Determine if file is targeted
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
            
        clean_name = (filename.lower()
                      .replace(".matrix.csv", "_matrix")
                      .replace(".csv", "")
                      .replace(".shp", "_shapefile")
                      .replace("__", "_")
                      .replace(".", "_")
                      .replace("-", "_"))
        
        # PostgreSQL limit safety: Truncate table names if they exceed 60 characters
        if len(clean_name) > 60:
            name_hash = hashlib.md5(clean_name.encode('utf-8')).hexdigest()[:6]
            clean_name = f"{clean_name[:50]}_{name_hash}"
        
        if any(name_lower.endswith(ext) for ext in [".shx", ".dbf", ".prj", ".cpg"]):
            continue

        # Dynamic Route: Handle WorldPop files differently by merging them into one
        if name_lower.startswith("worldpop_"):
            try:
                print(f"🌍 Reading WorldPop Component: '{filename}'")
                raw_df = pd.read_csv(file_path)
                processed_df = clean_dataframe(raw_df)
                
                # Determine metric column name in the raw dataframe
                metric_col = next((col for col in processed_df.columns if col in ['value', 'cases', 'confirmed_cases']), None)
                if not metric_col:
                    metric_col = processed_df.select_dtypes(include=['number']).columns[-1]

                # Identify joining keys
                join_keys = [col for col in ['health_zone', 'province'] if col in processed_df.columns]
                if not join_keys:
                    join_keys = [processed_df.columns[0]]
                
                subset_df = processed_df[join_keys + [metric_col]].copy()
                
                if "density" in name_lower:
                    subset_df = subset_df.rename(columns={metric_col: "density"})
                    worldpop_dfs["density"] = subset_df
                else:
                    subset_df = subset_df.rename(columns={metric_col: "count"})
                    worldpop_dfs["count"] = subset_df
                
                continue 
            except Exception as e:
                print(f"❌ Failed to extract WorldPop segment '{filename}': {e}")
                continue

        print(f"📦 Re-building Table: '{clean_name}' from raw file...")
        
        try:
            if name_lower.endswith(".shp"):
                processed_df = process_shapefile(file_path)
            else:
                raw_df = pd.read_csv(file_path)
                processed_df = clean_dataframe(raw_df)
            
            # Save normal table to database
            processed_df.to_sql(clean_name, engine, if_exists='replace', index=False)
            print(f"✔ Table '{clean_name}' completely replaced.")
            processed_count += 1
            
        except Exception as e:
            print(f"❌ Failed to process '{filename}': {e}")

    # ==========================================
    # Dynamic Join: Process & Merge WorldPop
    # ==========================================
    if worldpop_dfs["count"] is not None or worldpop_dfs["density"] is not None:
        try:
            print("🔗 Merging WorldPop dataframes...")
            
            if worldpop_dfs["count"] is not None and worldpop_dfs["density"] is not None:
                keys_count = [c for c in worldpop_dfs["count"].columns if c != "count"]
                keys_density = [c for c in worldpop_dfs["density"].columns if c != "density"]
                common_keys = list(set(keys_count).intersection(keys_density))
                
                merged_worldpop = pd.merge(worldpop_dfs["count"], worldpop_dfs["density"], on=common_keys, how="outer")
            else:
                merged_worldpop = worldpop_dfs["count"] if worldpop_dfs["count"] is not None else worldpop_dfs["density"]
            
            # 🎯 REMOVE metric columns 'count' and 'density' entirely
            cols_to_drop = [col for col in ['count', 'density'] if col in merged_worldpop.columns]
            merged_worldpop = merged_worldpop.drop(columns=cols_to_drop, errors='ignore')
            
            # De-duplicate the remaining geographic entries
            merged_worldpop = merged_worldpop.drop_duplicates()
            
            # Write only geographic keys to 'worldpop_nom_count_density'
            merged_worldpop.to_sql("worldpop_nom_count_density", engine, if_exists='replace', index=False)
            print("✔ Table 'worldpop_nom_count_density' successfully built (metrics removed).")
            processed_count += 1
            
        except Exception as e:
            print(f"❌ Failed to join and write combined WorldPop table: {e}")
            
    print(f"🎉 Complete! All previous tables cleared; {processed_count} unified tables deployed successfully.")

if __name__ == "__main__":
    clean_and_sync()
