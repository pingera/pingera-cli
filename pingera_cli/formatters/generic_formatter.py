
"""
Generic check result formatter for unknown types
"""

from typing import Dict, Any
from .base_formatter import BaseFormatter


class GenericFormatter(BaseFormatter):
    """Formatter for generic/unknown check results"""
    
    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Generic formatter can handle any metadata"""
        return True
    
    def format(self, metadata: Dict[str, Any]) -> str:
        """Format generic metadata"""
        info = "\n[bold cyan]Check Metadata:[/bold cyan]"
        
        # Display all metadata in a structured way
        for key, value in metadata.items():
            if isinstance(value, dict):
                info += f"\n• {key.replace('_', ' ').title()}:"
                info += self._format_dict_value(value)
            elif isinstance(value, list):
                info += f"\n• {key.replace('_', ' ').title()}: [white]{len(value)} items[/white]"
                info += self._format_list_value(value)
            else:
                display_value = self._truncate_text(str(value))
                info += f"\n• {key.replace('_', ' ').title()}: [white]{display_value}[/white]"
        
        return info
    
    def _format_dict_value(self, value: Dict[str, Any]) -> str:
        """Format dictionary values"""
        info = ""
        for sub_key, sub_value in value.items():
            if isinstance(sub_value, (str, int, float, bool)):
                info += f"\n  - {sub_key}: [white]{sub_value}[/white]"
        return info
    
    def _format_list_value(self, value: list) -> str:
        """Format list values"""
        info = ""
        # Show first few items
        for item in value[:3]:
            if isinstance(item, str):
                display_item = self._truncate_text(item, 50)
                info += f"\n  - [dim]{display_item}[/dim]"
        return info
