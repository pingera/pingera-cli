"""
Setup script for PingeraCLI package
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read version from __init__.py
def get_version():
    with open(os.path.join(this_directory, 'pingera_cli', '__init__.py'), 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('"')[1]
    return "0.1.0"

setup(
    name="pingera-cli",
    version=get_version(),
    author="PingeraCLI Team",
    author_email="support@pingera.com",
    description="A beautiful Python CLI tool built with typer and rich, distributed via pip and based on Pingera SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pingera/pingera-cli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Networking",
        "Topic :: Utilities",
        "Environment :: Console",
    ],
    python_requires=">=3.7",
    install_requires=[
        "typer[all]>=0.9.0",
        "rich>=13.0.0",
        "pingera-sdk",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ],
    },
    entry_points={
        "console_scripts": [
            "pngr=pingera_cli.main:cli_entry_point",
        ],
    },
    keywords="cli, pingera, network, monitoring, typer, rich, terminal",
    project_urls={
        "Bug Reports": "https://github.com/pingera/pingera-cli/issues",
        "Source": "https://github.com/pingera/pingera-cli",
        "Documentation": "https://docs.pingera.com/cli",
    },
)
