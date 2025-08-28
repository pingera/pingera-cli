
"""
Formatters for different check result types
"""

from .ssl_formatter import SSLFormatter
from .synthetic_formatter import SyntheticFormatter
from .multistep_formatter import MultistepFormatter
from .web_formatter import WebFormatter
from .generic_formatter import GenericFormatter
from .registry import FormatterRegistry

__all__ = ['SSLFormatter', 'SyntheticFormatter', 'MultistepFormatter', 'WebFormatter', 'GenericFormatter', 'FormatterRegistry']
