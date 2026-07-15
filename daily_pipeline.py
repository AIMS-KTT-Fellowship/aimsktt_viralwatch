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

def reorder_columns(df):
    """
    Reorders a DataFrame to guarantee:
    1st: Nom/Geographic Keys (health_zone, province)
    2nd: Count data (columns containing 'count')
    3rd: Density data (columns containing 'density')
    """
    cols = list(df.columns)
    
    # Identify and categorize columns
    key_cols = [c for c in cols if c in ['health_zone', 'province']]
    count_cols = [c for c in cols if 'count' in c and c not in key_cols]
    density_cols = [c for c in cols if 'density' in c and c not in key_cols]
    
    # Any other remaining columns
    other_cols = [c for c in cols if c not in key_cols and c not in count_cols and c not in density_cols]
    
    # Construct strictly ordered column list
    ordered_cols = key_cols + count_cols + density_cols + other_cols
    return df[ordered_cols]

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
    
    # Structures to hold files for merging
    worldpop_dfs = {"count": None, "density": None}
    crossborder_dfs = {}  # Dictionary mapping suffix -> DataFrame
    
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

        # Dynamic Route 1: Group WorldPop Components
        if name_lower.startswith("worldpop_"):
            try:
                print(f"🌍 Reading WorldPop Component: '{filename}'")
                raw_df = pd.read_csv(file_path)
                processed_df = clean_dataframe(raw_df)
                
                if "density" in name_lower:
                    worldpop_dfs["density"] = processed_df
                else:
                    worldpop_dfs["count"] = processed_df
                continue 
            except Exception as e:
                print(f"❌ Failed to extract WorldPop segment '{filename}': {e}")
                continue

        # Dynamic Route 2: Group Crossborder Components
        if name_lower.startswith("cross_border"):
            try:
                print(f"🛂 Reading Cross-border Component: '{filename}'")
                raw_df = pd.read_csv(file_path)
                processed_df = clean_dataframe(raw_df)
                
                # Determine suffix based on name identifiers
                if "density" in name_lower:
                    suffix = "density"
                elif "count" in name_lower or "pop" in name_lower:
                    suffix = "count"
                else:
                    suffix = name_lower.replace("cross_border_", "").replace(".csv", "")[:15]
                
                crossborder_dfs[suffix] = processed_df
                continue
            except Exception as e:
                print(f"❌ Failed to extract Cross-border segment '{filename}': {e}")
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
    # Dynamic Join: Merge & Order WorldPop
    # ==========================================
    if worldpop_dfs["count"] is not None or worldpop_dfs["density"] is not None:
        try:
            print("🔗 Merging and formatting WorldPop dataframes...")
            if worldpop_dfs["count"] is not None and worldpop_dfs["density"] is not None:
                keys_count = list(worldpop_dfs["count"].columns)
                keys_density = list(worldpop_dfs["density"].columns)
                common_keys = [col for col in keys_count if col in keys_density and col in ['health_zone', 'province']]
                if not common_keys:
                    common_keys = [keys_count[0]]
                
                merged_worldpop = pd.merge(
                    worldpop_dfs["count"], 
                    worldpop_dfs["density"], 
                    on=common_keys, 
                    how="outer", 
                    suffixes=('_count', '_density')
                )
            else:
                merged_worldpop = worldpop_dfs["count"] if worldpop_dfs["count"] is not None else worldpop_dfs["density"]
            
            # Reorder columns: [Names] -> [Count] -> [Density]
            merged_worldpop = reorder_columns(merged_worldpop)
            
            merged_worldpop.to_sql("worldpop_nom_count_density", engine, if_exists='replace', index=False)
            print("✔ Table 'worldpop_nom_count_density' successfully built (correct columns ordered!).")
            processed_count += 1
        except Exception as e:
            print(f"❌ Failed to join combined WorldPop table: {e}")

    # ==========================================
    # Dynamic Join: Merge & Order Crossborder
    # ==========================================
    if crossborder_dfs:
        try:
            print("🔗 Merging and formatting Cross-border dataframes...")
            suffixes = list(crossborder_dfs.keys())
            
            merged_cb = crossborder_dfs[suffixes[0]]
            keys_cb = [col for col in merged_cb.columns if col in ['health_zone', 'province']]
            if not keys_cb:
                keys_cb = [merged_cb.columns[0]]
                
            merged_cb = merged_cb.rename(
                columns={c: f"{c}_{suffixes[0]}" for c in merged_cb.columns if c not in keys_cb}
            )
            
            for _suff in suffixes[1:]:
                next_df = crossborder_dfs[_suff]
                next_keys = [col for col in next_df.columns if col in ['health_zone', 'province']]
                if not next_keys:
                    next_keys = [next_df.columns[0]]
                
                join_on = list(set(keys_cb).intersection(next_keys))
                if not join_on:
                    join_on = [keys_cb[0]]
                
                next_df_renamed = next_df.rename(
                    columns={c: f"{c}_{_suff}" for c in next_df.columns if c not in join_on}
                )
                
                merged_cb = pd.merge(merged_cb, next_df_renamed, on=join_on, how="outer")
            
            # Reorder columns: [Names] -> [Count] -> [Density]
            merged_cb = reorder_columns(merged_cb)
            
            merged_cb.to_sql("crossborder_nom_count_density", engine, if_exists='replace', index=False)
            print("✔ Table 'crossborder_nom_count_density' successfully built (correct columns ordered!).")
            processed_count += 1
        except Exception as e:
            print(f"❌ Failed to join combined Cross-border table: {e}")
            
    print(f"🎉 Complete! All previous tables cleared; {processed_count} unified tables deployed successfully.")

if __name__ == "__main__":
    clean_and_sync()
