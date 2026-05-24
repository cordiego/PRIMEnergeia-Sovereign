#!/bin/bash

# =================================================================
# PROJECT: diegocordoba (PRIMEnergeia & Eureka)
# PURPOSE: Automated Environment & Directory Optimization
# =================================================================

PROJECT_NAME="diegocordoba"

echo "--- Initializing Research Environment: $PROJECT_NAME ---"

# 1. Create Directory Hierarchy
echo "[1/4] Creating optimized directory structure..."
mkdir -p src/common src/primenergeia src/eureka
mkdir -p data/raw data/processed
mkdir -p notebooks tests config

# Create __init__.py files
touch src/__init__.py src/common/__init__.py src/primenergeia/__init__.py src/eureka/__init__.py

# 2. Virtual Environment Setup
echo "[2/4] Setting up Python Virtual Environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists. Skipping."
fi

# 3. Dependency Installation
echo "[3/4] Installing high-performance libraries..."
source .venv/bin/activate
pip install --upgrade pip
pip install numpy scipy torch matplotlib ipython

# 4. Finalizing Configuration
echo "[4/4] Creating base configuration files..."
cat <<EOF > config/settings.json
{
    "project": "PRIMEnergeia",
    "author": "Diego Cordoba",
    "default_rho": 2.0,
    "assets": ["SNDK", "SNXX", "CASH"]
}
EOF

echo "--- Setup Complete ---"
echo "To start working, run: source .venv/bin/activate"

