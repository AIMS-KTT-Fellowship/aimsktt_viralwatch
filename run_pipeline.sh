#!/bin/bash
# ==============================================================================
# ViralWatch Pipeline - Team Automation Script
# Runs the environment setup, dependency installation, and pipeline sync.
# ==============================================================================

# Exit immediately if a command fails
set -e

echo "🚀 Starting ViralWatch pipeline setup..."

# 1. Scaffolding Folders
echo "📂 Setting up local directories..."
mkdir -p data/raw data/processed models documentation

# 2. Virtual Environment Setup
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✔ Virtual environment already exists."
fi

# 3. Activate and Install Dependencies
echo "⚡ Activating environment and installing requirements..."
source venv/bin/activate
pip install -r requirements.txt

# 4. Run Step 1: Data Ingest (need update)
echo "📥 Syncing remote INRB-UMIE data repository..."
chmod +x download_data.sh
./download_data.sh

# 5. Run Step 2: Cleaning & Database Load 
echo "🧹 Processing and synchronizing databases..."
python3 daily_pipeline.py

echo "🎉 PIPELINE COMPLETE: Database is successfully loaded and ready!"
