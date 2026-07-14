cat << 'EOF' > download_data.sh
#!/bin/bash
set -e

REPO_URL="https://github.com/INRB-UMIE/BDBV2026-Data.git"
REPO_DIR="BDBV2026-Data"

echo "=== 1. Cleaning local directories ==="
rm -rf data_test
mkdir -p data_test

echo "=== 2. Testing Repository Reachability ==="
if git ls-remote "$REPO_URL" > /dev/null 2>&1; then
    echo "✔ Connection successful! The GitHub repository is reachable."
else
    echo "❌ CONNECTION ERROR: Cannot reach $REPO_URL. Check your internet connection or repository permissions." >&2
    exit 1
fi

echo "=== 3. Cloning Repository ==="
rm -rf "$REPO_DIR"
# Clone without depth limitation to ensure we grab everything
git clone "$REPO_URL"

echo "=== 4. Diagnosing Repository Structure ==="
echo "📂 Top-level files and folders inside cloned repo:"
ls -la "$REPO_DIR"

echo "🔍 Searching for ANY CSV files recursively..."
find "$REPO_DIR" -name "*.csv"

echo "=== 5. Copying CSVs if they exist ==="
CSV_FOUND=$(find "$REPO_DIR" -name "*.csv" | wc -l)

if [ "$CSV_FOUND" -gt 0 ]; then
    echo "✔ Found $CSV_FOUND CSV files! Copying them to data_test/..."
    find "$REPO_DIR" -name "*.csv" -exec cp {} data_test/ \;
else
    echo "⚠️ WARNING: No files with extension '.csv' were found."
    echo "Checking for alternative formats or compressed files..."
    ls -R "$REPO_DIR"
fi

echo "=== 6. Fetching WHO Bulletins ==="
curl -L -s -o data_test/DON602.html "https://www.who.int/emergencies/disease-outbreak-news/item/DON602"
curl -L -s -o data_test/DON603.html "https://www.who.int/emergencies/disease-outbreak-news/item/DON603"

echo "=== 7. Final Verification ==="
CSV_COUNT=$(ls data_test/*.csv 2>/dev/null | wc -l)
if [ "$CSV_COUNT" -gt 0 ]; then
    echo "✔ Ingestion successful! $CSV_COUNT files copied to data_test/."
else
    echo "❌ INGESTION ERROR: No CSV files are present in data_test/."
    exit 1
fi
EOF
