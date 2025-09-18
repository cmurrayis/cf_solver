#!/usr/bin/env python3
"""
Install Missing Dependencies for CloudflareScraper Python 3.9

This script installs all missing dependencies that weren't in the original requirements.
"""

import subprocess
import sys

def install_package(package):
    """Install a package using pip"""
    try:
        print(f"Installing {package}...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", package],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {package} installed successfully")
            return True
        else:
            print(f"❌ Failed to install {package}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing {package}: {e}")
        return False

def main():
    """Install all missing dependencies"""
    print("Installing Missing Dependencies for CloudflareScraper")
    print("=" * 55)

    # List of missing dependencies commonly needed
    missing_deps = [
        "psutil",           # For system monitoring
        "dataclasses",      # For Python 3.9 dataclass support (if needed)
        "typing-extensions", # For enhanced typing support
        "certifi",          # For SSL certificates
        "charset-normalizer", # For character encoding
        "idna",             # For internationalized domain names
        "urllib3",          # For HTTP requests
        "multidict",        # For aiohttp
        "yarl",             # For URL parsing
        "async-timeout",    # For async operations
        "aiosignal",        # For aiohttp signals
        "frozenlist",       # For aiohttp
        "attrs"             # For class definitions
    ]

    success_count = 0

    for package in missing_deps:
        if install_package(package):
            success_count += 1

    print(f"\n✅ Successfully installed {success_count}/{len(missing_deps)} packages")

    # Test import
    print("\nTesting CloudflareScraper import...")
    try:
        import cloudflare_research as cfr
        print("✅ CloudflareScraper imported successfully!")

        # Quick functionality test
        print("\nTesting basic functionality...")
        scraper = cfr.create_scraper()
        print("✅ Scraper created successfully!")
        scraper.close()
        print("✅ All tests passed!")

    except ImportError as e:
        print(f"❌ Import still failing: {e}")
        print("You may need to install additional dependencies manually")
    except Exception as e:
        print(f"⚠️ Import successful but functionality test failed: {e}")

if __name__ == "__main__":
    main()