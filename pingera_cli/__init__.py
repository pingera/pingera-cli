"""
Pingera CLI - A beautiful CLI tool for Pingera Platform
"""

__version__ = "0.1.8"
__author__ = "Pingera Team"
__description__ = "A beautiful Python CLI tool built with typer and rich, distributed via pip and based on Pingera SDK"

from .main import app

__all__ = ["app", "__version__"]
