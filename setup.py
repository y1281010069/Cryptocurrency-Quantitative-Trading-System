#!/usr/bin/env python3
"""
专业量化交易系统安装配置
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="quantitative-trading-system",
    version="3.0.0",
    author="Professional Trading Team",
    author_email="contact@trading-system.com",
    description="专业的加密货币量化交易系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/quantitative-trading-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ultimate-profit=ultimate_profit_system:main",
            "multi-timeframe=multi_timeframe_system:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    keywords="cryptocurrency trading quantitative finance algorithmic bitcoin",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/quantitative-trading-system/issues",
        "Source": "https://github.com/yourusername/quantitative-trading-system",
        "Documentation": "https://github.com/yourusername/quantitative-trading-system/wiki",
    },
) 