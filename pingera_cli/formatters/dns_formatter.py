"""
DNS check result formatter
"""

from typing import Dict, Any
from .base_formatter import BaseFormatter


class DnsFormatter(BaseFormatter):
    """Formatter for DNS check results"""

    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this is DNS metadata"""
        return 'records' in metadata or 'nameservers' in metadata

    def format(self, metadata: Dict[str, Any]) -> str:
        """Format DNS check metadata"""
        info = "\n[bold cyan]DNS Query Results:[/bold cyan]"

        # Query information
        if 'query_type' in metadata:
            info += f"\n• Query Type: [white]{metadata['query_type']}[/white]"
        if 'domain' in metadata:
            info += f"\n• Domain: [white]{metadata['domain']}[/white]"

        # DNS Records
        if 'records' in metadata and metadata['records']:
            records = metadata['records']
            info += f"\n• Records Found: [green]{len(records)}[/green]"

            # Show first few records
            display_records = records if self.verbose else records[:5]
            for record in display_records:
                record_type = record.get('type', 'Unknown')
                record_value = record.get('value', 'N/A')
                info += f"\n  • [{record_type}] {record_value}"

            if not self.verbose and len(records) > 5:
                info += f"\n  [dim]... and {len(records) - 5} more records[/dim]"
                info += self._get_truncation_note()

        # Nameservers
        if 'nameservers' in metadata and metadata['nameservers']:
            nameservers = metadata['nameservers']
            info += f"\n• Nameservers: [white]{', '.join(nameservers)}[/white]"

        # Query time
        if 'query_time' in metadata:
            info += f"\n• Query Time: [yellow]{metadata['query_time']}ms[/yellow]"

        return info