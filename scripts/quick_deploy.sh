#!/bin/bash
# Quick Deployment Script for CloudflareBypass Research Tool
# Run this on a remote server to quickly test the bypass capability

set -e  # Exit on any error

echo "=== CloudflareBypass Research Tool - Quick Deploy ==="
echo "Starting deployment at $(date)"

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    echo "WARNING: Running as root is not recommended"
    echo "Consider creating a dedicated user for testing"
fi

# Update system packages
echo "Updating system packages..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv git curl build-essential libssl-dev libffi-dev
elif command -v yum &> /dev/null; then
    sudo yum update -y
    sudo yum install -y python3 python3-pip git curl gcc openssl-devel libffi-devel
elif command -v apk &> /dev/null; then
    sudo apk update
    sudo apk add python3 py3-pip git curl build-base openssl-dev libffi-dev
fi

# Create working directory
WORK_DIR="$HOME/cloudflare-bypass-test"
echo "Creating working directory: $WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Clone repository (you'll need to update this URL)
REPO_URL="${1:-https://github.com/yourusername/cloudflare-bypass-research.git}"
echo "Cloning repository: $REPO_URL"

if [ -d "cloudflare-bypass-research" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd cloudflare-bypass-research
    git pull
else
    git clone "$REPO_URL"
    cd cloudflare-bypass-research
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Verify installation
echo "Verifying installation..."
python -c "import cloudflare_research; print('✓ CloudflareBypass module imported successfully')"
python -c "from mini_racer import MiniRacer; print('✓ MiniRacer available')"
python -c "import aiohttp; print('✓ aiohttp available')"

# Get system information
echo "=== System Information ==="
echo "Python version: $(python --version)"
echo "Platform: $(uname -a)"
echo "IP Location: $(curl -s https://ipapi.co/json/ | python -m json.tool 2>/dev/null || echo 'Location check failed')"

# Run tests
echo "=== Running Tests ==="

# Test 1: Quick functionality test
echo "Running quick functionality test..."
python -c "
import asyncio
from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig

async def quick_test():
    config = CloudflareBypassConfig(max_concurrent_requests=5)
    try:
        async with CloudflareBypass(config) as bypass:
            result = await bypass.get('https://httpbin.org/get')
            print(f'✓ Quick test passed: Status {result.status_code}')
    except Exception as e:
        print(f'✗ Quick test failed: {e}')

asyncio.run(quick_test())
"

# Test 2: Detailed bypass analysis (if target provided)
TARGET_URL="${2:-https://kick.com/api/v1/channels/adinross}"
echo "Running detailed bypass analysis against: $TARGET_URL"

# Modify the analysis script to use provided target
if [ "$#" -ge 2 ]; then
    # Create a custom test script with the provided target
    cat > custom_test.py << EOF
import asyncio
from tests.detailed_bypass_analysis import DetailedBypassAnalyzer

async def main():
    analyzer = DetailedBypassAnalyzer("$TARGET_URL")
    report = await analyzer.run_detailed_analysis(concurrent_requests=5)
    analyzer.print_final_report(report)

if __name__ == "__main__":
    asyncio.run(main())
EOF
    python custom_test.py
else
    # Use default test
    python tests/detailed_bypass_analysis.py
fi

# Create summary report
echo "=== Deployment Summary ==="
echo "Deployment completed at: $(date)"
echo "Working directory: $(pwd)"
echo "Virtual environment: venv/"
echo "Test results: detailed_bypass_analysis.json"

# Instructions for manual testing
echo ""
echo "=== Manual Testing Instructions ==="
echo "To run additional tests manually:"
echo "1. Activate environment: source venv/bin/activate"
echo "2. Run detailed analysis: python tests/detailed_bypass_analysis.py"
echo "3. Run concurrency test: python tests/high_concurrency_test.py"
echo "4. Run performance test: python tests/performance_report.py"
echo ""
echo "To test against custom target:"
echo "python -c \"
import asyncio
from cloudflare_research.bypass import CloudflareBypass, CloudflareBypassConfig

async def test_custom():
    config = CloudflareBypassConfig(max_concurrent_requests=10)
    async with CloudflareBypass(config) as bypass:
        result = await bypass.get('YOUR_TARGET_URL')
        print(f'Status: {result.status_code}, Success: {result.success}')

asyncio.run(test_custom())
\""

echo ""
echo "🎉 Deployment completed successfully!"
echo "Virtual environment activated and ready for testing."