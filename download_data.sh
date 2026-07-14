#!/bin/bash
set -e

# Target repository to clone from
REPO_URL="https://github.com/INRB-UMIE/BDBV2026-Data.git"
REPO_DIR="BDBV2026-Data"

echo "🧹 Preparing local directories..."
rm -rf data_test
mkdir -p data_test

echo "🚀 Cloning BDBV2026-Data Repository..."
rm -rf "$REPO_DIR"
git clone "$REPO_URL"

echo "🔍 Searching and copying target dataset files..."

# Find and copy files, renaming them to match your pipeline's target expectations
find "$REPO_DIR" -name "*cases*.csv" -o -name "*Cases*.csv" -exec cp {} data_test/BDBV2026_Cases_HA.csv \;
find "$REPO_DIR" -name "*displacement*.csv" -o -name "*idp*.csv" -exec cp {} data_test/idp_displacement.csv \;
find "$REPO_DIR" -name "*vulnerability*.csv" -o -name "*ccvi*.csv" -exec cp {} data_test/ccvi_vulnerability_index.csv \;
find "$REPO_DIR" -name "*mobility*.csv" -o -name "*flowminder*.csv" -exec cp {} data_test/flowminder_mobility.csv \;

# If recursive exact matches failed, fallback to copy any available CSVs into data_test/
CSV_COPIED=$(ls -1 data_test/*.csv 2>/dev/null | wc -l)
if [ "$CSV_COPIED" -eq 0 ]; then
    echo "⚠️ Target file names not found. Harvesting all available CSV files..."
    find "$REPO_DIR" -name "*.csv" -exec cp {} data_test/ \;
fi

echo "🌍 Downloading supplementary WHO Outbreak bulletins..."
curl -L -s -o data_test/DON602.html "https://www.who.int/emergencies/disease-outbreak-news/item/DON602"
curl -L -s -o data_test/DON603.html "https://www.who.int/emergencies/disease-outbreak-news/item/DON603"

# Final validation
FINAL_COUNT=$(ls -1 data_test/*.csv 2>/dev/null | wc -l)
if [ "$FINAL_COUNT" -gt 0 ]; then
    echo "✔ Ingestion Complete! $FINAL_COUNT dataset files successfully copied to data_test/."
else
    echo "❌ INGESTION ERROR: No CSV data files could be retrieved." >&2
    exit 1
fi
