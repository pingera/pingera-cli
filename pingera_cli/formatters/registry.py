"""
Formatter registry for managing different check result formatters
"""

from typing import Dict, Any, List
from .base_formatter import BaseFormatter
from .ssl_formatter import SSLFormatter
from .synthetic_formatter import SyntheticFormatter
from .multistep_formatter import MultistepFormatter
from .web_formatter import WebFormatter
from .icmp_formatter import ICMPFormatter
from .dns_formatter import DNSFormatter
from .portscan_formatter import PortscanFormatter
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
            ICMPFormatter(verbose),
            DNSFormatter(verbose),
            PortscanFormatter(verbose),
            GenericFormatter(verbose)  # Generic formatter should be last
        ]

    def format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata using the appropriate formatter"""
        # Add result_id to metadata if not present for truncation notices
        if 'result_id' not in metadata and isinstance(metadata, dict):
            # result_id might be in the parent context, but we'll handle it in formatters
            pass

        for formatter in self.formatters:
            if formatter.can_format(metadata):
                return formatter.format(metadata)

        # Fallback to generic formatter
        return self.formatters[-1].format(metadata)