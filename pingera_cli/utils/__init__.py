"""
Utilities module for PingeraCLI
"""

from .console import console, error_console
from .config import get_config, save_config

__all__ = ["console", "error_console", "get_config", "save_config"]
