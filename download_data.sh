cat << 'EOF' > download_data.sh
#!/bin/bash
set -e

REPO_URL="https://github.com/INRB-UMIE/BDBV2026-Data.git"
REPO_DIR="BDBV2026-Data"

echo "=== 1. Scaffolding Local Project Structure ==="
mkdir -p data/raw data/processed models documentation

echo "=== 2. Cloning/Updating INRB-UMIE Repository ==="
if [ ! -d "$REPO_DIR" ]; then
    echo "Cloning the repository..."
    git clone --depth 1 "$REPO_URL"
else
    echo "Repository already exists. Pulling latest..."
    git -C "$REPO_DIR" pull
fi

echo "=== 3. Organizing Ingested Data ==="
cp "$REPO_DIR"/data/*.csv data/raw/ 2>/dev/null || cp "$REPO_DIR"/*.csv data/raw/

echo "=== 4. Fetching WHO Bulletins ==="
curl -L -s -o data/raw/DON602.html "https://www.who.int/emergencies/disease-outbreak-news/item/DON602"
curl -L -s -o data/raw/DON603.html "https://www.who.int/emergencies/disease-outbreak-news/item/DON603"

echo "=== 5. Verifying Integrity ==="
if [ -f "data/raw/BDBV2026_Cases_HA.csv" ]; then
    echo "✔ Ingestion verification successful!"
else
    echo "❌ INGESTION ERROR: Core files missing." >&2
    exit 1
fi
EOF
