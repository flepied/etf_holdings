#!/usr/bin/env python3
"""
Setup script for ETF Holdings Library
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="etf-holdings",
    version="1.0.0",
    author="ETF Holdings Team",
    description="Extract ETF holdings data from SEC N-PORT filings",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: Apache License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "pandas>=1.3.0",
        "lxml>=4.6.0",
        "sec-edgar-downloader>=5.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-xdist>=2.0",  # For parallel test execution
            "black>=21.0",
            "flake8>=3.8",
        ],
    },
    entry_points={
        "console_scripts": [
            "etf-holdings=etf_holdings.cli:main",
        ],
    },
)
