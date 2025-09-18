#!/usr/bin/env python3
"""
Fix Python 3.9 Compatibility for CloudflareScraper

This script modifies the CloudflareScraper to work with Python 3.9
"""

import os
import re

def fix_setup_py():
    """Fix setup.py to allow Python 3.9"""
    print("Fixing setup.py for Python 3.9 compatibility...")

    if os.path.exists("setup.py"):
        with open("setup.py", "r") as f:
            content = f.read()

        # Replace Python requirement
        content = re.sub(r'python_requires=["\']>=3\.11["\']', 'python_requires=">=3.9"', content)
        content = re.sub(r'"Programming Language :: Python :: 3\.11"', '"Programming Language :: Python :: 3.9"', content)

        with open("setup.py", "w") as f:
            f.write(content)

        print("✅ Fixed setup.py")
    else:
        print("❌ setup.py not found")

def fix_pyproject_toml():
    """Fix pyproject.toml if it exists"""
    print("Checking pyproject.toml...")

    if os.path.exists("pyproject.toml"):
        with open("pyproject.toml", "r") as f:
            content = f.read()

        # Replace Python requirement
        content = re.sub(r'requires-python = ">=3\.11"', 'requires-python = ">=3.9"', content)

        with open("pyproject.toml", "w") as f:
            f.write(content)

        print("✅ Fixed pyproject.toml")
    else:
        print("ℹ️ pyproject.toml not found (OK)")

def fix_type_hints():
    """Fix Python 3.11+ type hints for 3.9 compatibility"""
    print("Fixing type hints for Python 3.9...")

    import glob

    # Find all Python files
    py_files = glob.glob("**/*.py", recursive=True)

    fixes_made = 0

    for file_path in py_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content

            # Fix Union syntax (Python 3.10+)
            # Replace: str | int with Union[str, int]
            content = re.sub(r'\b(\w+)\s*\|\s*(\w+)', r'Union[\1, \2]', content)

            # Add typing imports if Union is used but not imported
            if 'Union[' in content and 'from typing import' in content:
                if 'Union' not in content.split('Union[')[0]:
                    content = re.sub(r'from typing import ([^\\n]+)', r'from typing import \1, Union', content)
            elif 'Union[' in content and 'import typing' not in content:
                # Add typing import at the top
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        lines.insert(i, 'from typing import Union')
                        break
                content = '\n'.join(lines)

            # Fix other 3.11+ features if needed
            # Add more fixes here as needed

            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                fixes_made += 1
                print(f"  ✅ Fixed: {file_path}")

        except Exception as e:
            print(f"  ⚠️ Warning: Could not process {file_path}: {e}")

    print(f"✅ Applied fixes to {fixes_made} files")

def create_requirements_39():
    """Create Python 3.9 compatible requirements"""
    print("Creating Python 3.9 compatible requirements...")

    requirements_39 = """
# Python 3.9 Compatible Requirements for CloudflareScraper

# Core HTTP and async
aiohttp>=3.8.0,<4.0.0
asyncio-throttle>=1.0.0

# TLS and fingerprinting
curl-cffi>=0.5.0,<1.0.0

# JavaScript execution
py-mini-racer>=0.6.0

# Data validation and models
pydantic>=1.10.0,<2.0.0

# Utilities
fake-useragent>=1.2.0
lxml>=4.9.0
beautifulsoup4>=4.11.0

# Development dependencies (optional)
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-mock>=3.10.0

# Documentation (optional)
sphinx>=5.0.0
sphinx-rtd-theme>=1.2.0
"""

    with open("requirements_python39.txt", "w") as f:
        f.write(requirements_39.strip())

    print("✅ Created requirements_python39.txt")

def main():
    """Main execution"""
    print("=" * 60)
    print("  CLOUDFLARE SCRAPER - PYTHON 3.9 COMPATIBILITY FIX")
    print("=" * 60)
    print("Making CloudflareScraper compatible with Python 3.9...")
    print()

    # Check current directory
    if not os.path.exists("cloudflare_research"):
        print("❌ Error: Not in CloudflareScraper directory")
        print("Please run this in the CF_Solver directory")
        return

    # Apply fixes
    fix_setup_py()
    fix_pyproject_toml()
    fix_type_hints()
    create_requirements_39()

    print("\n" + "=" * 60)
    print("  COMPATIBILITY FIXES APPLIED")
    print("=" * 60)
    print("Now try installing with:")
    print()
    print("1. pip install -r requirements_python39.txt")
    print("2. pip install -e .")
    print()
    print("If that still fails, try manual installation:")
    print("pip install aiohttp curl-cffi py-mini-racer pydantic fake-useragent")
    print("pip install -e . --no-deps")

if __name__ == "__main__":
    main()