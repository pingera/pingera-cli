
"""
Base formatter class for check results
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseFormatter(ABC):
    """Base class for all result formatters"""
    
    def __init__(self, verbose: bool = False, job_id: str = None, result_id: str = None):
        self.verbose = verbose
        self.job_id = job_id
        self.result_id = result_id
    
    @abstractmethod
    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this formatter can handle the given metadata"""
        pass
    
    @abstractmethod
    def format(self, metadata: Dict[str, Any]) -> str:
        """Format the metadata into a rich string"""
        pass
    
    def _truncate_text(self, text: str, max_length: int = 100) -> str:
        """Truncate text if it's too long"""
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        if size_bytes > 1024*1024:
            return f"{size_bytes/(1024*1024):.1f}MB"
        elif size_bytes > 1024:
            return f"{size_bytes/1024:.1f}KB"
        elif size_bytes > 0:
            return f"{size_bytes}B"
        else:
            return "0B"
    
    def _format_duration(self, duration_ms: float) -> str:
        """Format duration in milliseconds"""
        return f"{duration_ms:.0f}ms" if duration_ms > 0 else "0ms"
    
    def _get_truncation_note(self) -> str:
        """Get standardized truncation note with job ID and command"""
        if self.result_id:
            return f"\n\n[dim]💡 Some details truncated. Use --verbose flag or view full results at:[/dim]\n[dim]   https://app.pingera.ru/checks/results/{self.result_id}[/dim]\n[dim]   Or run: [white]pngr checks results --result-id {self.result_id}[/white][/dim]"
        elif self.job_id:
            return f"\n\n[dim]💡 Some details truncated. Use --verbose flag or view full results at:[/dim]\n[dim]   https://app.pingera.ru/checks/jobs/{self.job_id}[/dim]\n[dim]   Or run: [white]pngr checks jobs status {self.job_id} --verbose[/white][/dim]"
        else:
            return "\n\n[dim]💡 Some details truncated. Use --verbose flag for full results.[/dim]"
