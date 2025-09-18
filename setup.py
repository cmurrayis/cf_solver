#!/usr/bin/env python3
"""
Setup script for cloudflare_research module.
High-performance browser emulation for Cloudflare challenge research.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="cloudflare_research",
    version="1.0.0",
    author="CF Solver Research",
    author_email="research@example.com",
    description="High-performance browser emulation module for Cloudflare challenge research",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/cloudflare_research",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cloudflare-research=cloudflare_research.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)