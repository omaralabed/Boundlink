#!/usr/bin/env python3
"""Bondlink Client - Multi-WAN Bonding Router Setup"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bondlink-client",
    version="1.0.0",
    author="Bondlink Team",
    description="Production-ready multi-WAN bonding router client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/bondlink",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Networking",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.10",
    install_requires=[
        "psutil>=5.9.8",
        "netifaces>=0.11.0",
        "pyroute2>=0.7.12",
        "aiohttp>=3.9.0",
        "pyyaml>=6.0.1",
        "structlog>=24.1.0",
        "cryptography>=42.0.0",
        "click>=8.1.7",
        "rich>=13.7.0",
    ],
    entry_points={
        "console_scripts": [
            "bondlink=client.cli:main",
            "bondlink-daemon=client.daemon:main",
        ],
    },
)
