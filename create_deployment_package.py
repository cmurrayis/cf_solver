#!/usr/bin/env python3
"""
Create Deployment Package

This script creates a deployment package for uploading to your server.
"""

import os
import shutil
import zipfile
from pathlib import Path

def create_deployment_package():
    """Create a deployment package for server upload"""

    print("Creating CloudflareScraper Deployment Package")
    print("=" * 45)

    # Define package contents
    package_files = [
        # Core module
        "cloudflare_research/",

        # Requirements and setup
        "requirements.txt",
        "setup.py",

        # Documentation
        "README.md",
        "SECURITY.md",
        "ETHICAL_USAGE.md",

        # Test scripts
        "quick_server_test.py",
        "simple_cloudscraper_example.py",

        # Examples
        "cloudscraper_replacement_demo.py",
        "step_by_step_test.py",
        "cloudflare_detection_test.py",
    ]

    # Create deployment directory
    deploy_dir = Path("cloudflare_scraper_deployment")
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
    deploy_dir.mkdir()

    print("\n[COPY] Copying files to deployment package...")

    # Copy files
    copied_files = []
    for item in package_files:
        src_path = Path(item)
        if src_path.exists():
            dst_path = deploy_dir / item

            if src_path.is_dir():
                shutil.copytree(src_path, dst_path)
                print(f"   [DIR] {item}")
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                print(f"   [FILE] {item}")

            copied_files.append(item)
        else:
            print(f"   [MISSING] {item}")

    # Create server installation script
    install_script = deploy_dir / "install_on_server.sh"
    with open(install_script, 'w') as f:
        f.write('''#!/bin/bash
# CloudflareScraper Server Installation Script

echo "🚀 CloudflareScraper Server Installation"
echo "========================================"

# Check Python version
python_version=$(python3 --version 2>&1)
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv cloudflare_env
source cloudflare_env/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install CloudflareScraper
echo "🔧 Installing CloudflareScraper..."
pip install -e .

# Run test
echo ""
echo "🧪 Running deployment test..."
python quick_server_test.py

echo ""
echo "✅ Installation complete!"
echo ""
echo "To activate environment: source cloudflare_env/bin/activate"
echo "To test: python quick_server_test.py"
echo "To use: python simple_cloudscraper_example.py"
''')

    # Make script executable
    install_script.chmod(0o755)
    print(f"   [FILE] install_on_server.sh")

    # Create Python installation script (for Windows servers)
    install_py = deploy_dir / "install_on_server.py"
    with open(install_py, 'w') as f:
        f.write('''#!/usr/bin/env python3
"""
CloudflareScraper Server Installation Script (Python version)
For servers where bash is not available
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True,
                              capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False

def main():
    print("🚀 CloudflareScraper Server Installation")
    print("=" * 40)

    # Check Python version
    print(f"Python version: {sys.version}")

    if sys.version_info < (3, 11):
        print("⚠️  Warning: Python 3.11+ recommended")

    # Install dependencies
    if not run_command("pip install --upgrade pip", "Upgrading pip"):
        return False

    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return False

    if not run_command("pip install -e .", "Installing CloudflareScraper"):
        return False

    # Run test
    print("\\n🧪 Running deployment test...")
    try:
        subprocess.run([sys.executable, "quick_server_test.py"], check=True)
        print("\\n✅ Installation and test completed successfully!")
    except subprocess.CalledProcessError:
        print("\\n⚠️  Installation complete but test failed")
        print("   You may need to check dependencies or network connectivity")

    print("\\nNext steps:")
    print("1. Test: python quick_server_test.py")
    print("2. Use: python simple_cloudscraper_example.py")

if __name__ == "__main__":
    main()
''')
    print(f"   [FILE] install_on_server.py")

    # Create README for deployment
    readme = deploy_dir / "DEPLOYMENT_README.md"
    with open(readme, 'w') as f:
        f.write('''# CloudflareScraper Server Deployment

## Quick Start

### Option 1: Bash Installation (Linux/macOS)
```bash
chmod +x install_on_server.sh
./install_on_server.sh
```

### Option 2: Python Installation (Windows/Any)
```bash
python install_on_server.py
```

### Option 3: Manual Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Install CloudflareScraper
pip install -e .

# Test installation
python quick_server_test.py
```

## Testing Your Installation

1. **Quick Test**: `python quick_server_test.py`
2. **Basic Example**: `python simple_cloudscraper_example.py`
3. **Full Demo**: `python cloudscraper_replacement_demo.py`

## Using CloudflareScraper

```python
import cloudflare_research as cfr

# Just like cloudscraper!
scraper = cfr.create_scraper()
response = scraper.get("https://protected-site.com")
print(response.text)
```

## Files Included

- `cloudflare_research/` - Main module
- `requirements.txt` - Dependencies
- `setup.py` - Installation configuration
- `quick_server_test.py` - Test your installation
- `simple_cloudscraper_example.py` - Basic usage example
- `README.md` - Full documentation
- `SECURITY.md` - Security guidelines
- `ETHICAL_USAGE.md` - Ethical usage guidelines

## Support

See README.md for full documentation and troubleshooting.
''')
    print(f"   [FILE] DEPLOYMENT_README.md")

    # Create ZIP archive
    zip_path = Path("cloudflare_scraper_deployment.zip")
    if zip_path.exists():
        zip_path.unlink()

    print(f"\\n[ZIP] Creating ZIP archive...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(deploy_dir):
            for file in files:
                file_path = Path(root) / file
                arc_path = file_path.relative_to(deploy_dir.parent)
                zipf.write(file_path, arc_path)

    print(f"   ✅ Created: {zip_path}")

    # Summary
    print(f"\\n✅ Deployment package created successfully!")
    print(f"\\n📋 Package Contents:")
    print(f"   📁 Directory: {deploy_dir}")
    print(f"   📦 Archive: {zip_path}")
    print(f"   📄 Files: {len(copied_files)} included")

    print(f"\\n🚀 Deployment Instructions:")
    print(f"1. Upload {zip_path} to your server")
    print(f"2. Extract: unzip {zip_path}")
    print(f"3. Enter directory: cd {deploy_dir.name}")
    print(f"4. Run: ./install_on_server.sh (or python install_on_server.py)")
    print(f"5. Test: python quick_server_test.py")

    return zip_path

if __name__ == "__main__":
    create_deployment_package()