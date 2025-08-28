
"""
Formatter registry for managing different check result formatters
"""

from typing import Dict, Any, List
from .base_formatter import BaseFormatter
from .ssl_formatter import SSLFormatter
from .synthetic_formatter import SyntheticFormatter
from .multistep_formatter import MultistepFormatter
from .web_formatter import WebFormatter
from .generic_formatter import GenericFormatter


class FormatterRegistry:
    """Registry for managing check result formatters"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.formatters: List[BaseFormatter] = [
            SSLFormatter(verbose),
            SyntheticFormatter(verbose),
            MultistepFormatter(verbose),
            WebFormatter(verbose),
            GenericFormatter(verbose)  # Generic formatter should be last
        ]
    
    def format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata using the appropriate formatter"""
        for formatter in self.formatters:
            if formatter.can_format(metadata):
                return formatter.format(metadata)
        
        # This should never happen since GenericFormatter can handle anything
        return "\n[bold cyan]Check Metadata:[/bold cyan]\n• [dim]No formatter available[/dim]"
