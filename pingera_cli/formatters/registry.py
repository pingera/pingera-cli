"""
Formatter registry for managing all result formatters
"""

from typing import Dict, Any, List, Optional
from .base_formatter import BaseFormatter
from .web_formatter import WebFormatter
from .ssl_formatter import SSLFormatter
from .portscan_formatter import PortscanFormatter
from .multistep_formatter import MultistepFormatter
from .synthetic_formatter import SyntheticFormatter
from .icmp_formatter import IcmpFormatter
from .dns_formatter import DnsFormatter
from .generic_formatter import GenericFormatter


class FormatterRegistry:
    """Registry for managing all result formatters"""

    def __init__(self, verbose: bool = False, job_id: Optional[str] = None, result_id: Optional[str] = None):
        self.verbose = verbose
        self.job_id = job_id
        self.result_id = result_id
        self.formatters: List[BaseFormatter] = [
            WebFormatter(verbose, job_id, result_id),
            SSLFormatter(verbose, job_id, result_id),
            PortscanFormatter(verbose, job_id, result_id),
            MultistepFormatter(verbose, job_id, result_id),
            SyntheticFormatter(verbose, job_id, result_id),
            IcmpFormatter(verbose, job_id, result_id),
            DnsFormatter(verbose, job_id, result_id),
            GenericFormatter(verbose, job_id, result_id),  # Generic formatter as fallback
        ]

    def format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata using the appropriate formatter"""
        for formatter in self.formatters:
            if formatter.can_format(metadata):
                return formatter.format(metadata)

        # This should never happen since GenericFormatter can handle anything
        return "\n[bold cyan]Check Metadata:[/bold cyan]\n• [dim]No formatter available[/dim]"