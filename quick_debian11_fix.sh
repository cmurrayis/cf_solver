#!/bin/bash
# Quick Fix for CloudflareScraper on Debian 11

echo "========================================================"
echo "  CLOUDFLARE SCRAPER - DEBIAN 11 QUICK FIX"
echo "========================================================"
echo "Fixing Python 3.9 virtual environment issues..."
echo ""

# Update package list
echo "1. Updating package list..."
sudo apt update

# Install missing packages
echo "2. Installing missing packages..."
sudo apt install -y python3-venv python3-pip python3-dev
sudo apt install -y build-essential libcurl4-openssl-dev libssl-dev
sudo apt install -y pkg-config libffi-dev

# Remove old virtual environment
echo "3. Cleaning up old virtual environment..."
rm -rf cloudflare_env

# Create new virtual environment
echo "4. Creating virtual environment..."
python3 -m venv cloudflare_env

# Activate and test
echo "5. Testing virtual environment..."
source cloudflare_env/bin/activate
python --version

# Upgrade pip
echo "6. Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "7. Installing dependencies..."
pip install wheel setuptools
pip install -r requirements.txt

# Install CloudflareScraper
echo "8. Installing CloudflareScraper..."
pip install -e .

# Test import
echo "9. Testing import..."
python -c "import cloudflare_research as cfr; print('✅ Import successful!')"

echo ""
echo "========================================================"
echo "  SETUP COMPLETE!"
echo "========================================================"
echo "To use CloudflareScraper:"
echo "1. source cloudflare_env/bin/activate"
echo "2. python your_script.py"
echo ""
echo "Quick test:"
echo "python -c \"import cloudflare_research as cfr; print('Working!')\""