#!/bin/bash

set -e

PROJECT="BDBV2026-Project"

echo "Creating project: $PROJECT"

mkdir -p "$PROJECT"

cd "$PROJECT"

############################################
# Data
############################################

mkdir -p data/raw
mkdir -p data/processed
mkdir -p data/external

############################################
# Source Code
############################################

mkdir -p src

touch src/__init__.py

touch src/data_loader.py
touch src/preprocess.py
touch src/features.py
touch src/target.py
touch src/sklearn_model.py
touch src/keras_model.py
touch src/evaluate.py
touch src/plots.py

############################################
# Dashboard
############################################

mkdir -p dashboard
mkdir -p dashboard/components
mkdir -p dashboard/assets

touch dashboard/app.py
touch dashboard/components/charts.py
touch dashboard/components/maps.py
touch dashboard/components/tables.py

############################################
# Models
############################################

mkdir -p models

############################################
# Reports
############################################

mkdir -p reports
mkdir -p reports/figures

touch reports/final_report.md

############################################
# Scripts
############################################

mkdir -p scripts

touch scripts/download_data.sh
touch scripts/preprocess_data.sh
touch scripts/train_model.sh

############################################
# Notebooks
############################################

mkdir -p notebooks

touch notebooks/01_data_exploration.ipynb
touch notebooks/02_feature_engineering.ipynb
touch notebooks/03_model_training.ipynb
touch notebooks/04_model_evaluation.ipynb

############################################
# Tests
############################################

mkdir -p tests

touch tests/test_preprocess.py
touch tests/test_features.py
touch tests/test_models.py

############################################
# Main files
############################################

touch train.py
touch requirements.txt
touch README.md
touch .gitignore

############################################
# Python virtual environment
############################################

python3 -m venv .venv

############################################
# Gitignore
############################################

cat > .gitignore << EOF
.venv/
__pycache__/
*.pyc
.ipynb_checkpoints/
models/*.pkl
models/*.keras
reports/figures/
EOF

############################################
# Requirements
############################################

cat > requirements.txt << EOF
numpy
pandas
matplotlib
seaborn
plotly
geopandas
folium
scikit-learn
tensorflow
keras
imbalanced-learn
joblib
streamlit
pytest
jupyter
notebook
EOF

echo ""
echo "======================================="
echo "Project created successfully!"
echo "======================================="
echo ""

tree .