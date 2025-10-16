
"""
DNS check result formatter
"""

from typing import Dict, Any, List
from .base_formatter import BaseFormatter


class DNSFormatter(BaseFormatter):
    """Formatter for DNS check results"""
    
    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this is DNS metadata"""
        return 'record_type' in metadata and 'answers' in metadata
    
    def format(self, metadata: Dict[str, Any]) -> str:
        """Format DNS check metadata"""
        info = "\n[bold cyan]DNS Query Results:[/bold cyan]"
        
        # Query information
        if 'domain' in metadata:
            info += f"\n• Domain: [white]{metadata['domain']}[/white]"
        if 'record_type' in metadata:
            info += f"\n• Record Type: [blue]{metadata['record_type']}[/blue]"
        
        # DNS servers used
        if 'dns_servers_used' in metadata:
            servers = metadata['dns_servers_used']
            if servers == 'system_default':
                info += f"\n• DNS Servers: [dim]System Default[/dim]"
            elif isinstance(servers, list):
                info += f"\n• DNS Servers: [white]{', '.join(servers)}[/white]"
            else:
                info += f"\n• DNS Servers: [white]{servers}[/white]"
        
        # Validation mode
        if 'validation_mode' in metadata and metadata['validation_mode'] != 'none':
            info += f"\n• Validation Mode: [white]{metadata['validation_mode']}[/white]"
        
        # DNS answers
        if 'answers' in metadata and metadata['answers']:
            info += "\n\n[bold cyan]DNS Answers:[/bold cyan]"
            for answer in metadata['answers']:
                info += f"\n• [green]{answer}[/green]"
        elif 'answers' in metadata:
            info += "\n\n[bold cyan]DNS Answers:[/bold cyan]"
            info += f"\n• [yellow]No records found[/yellow]"
        
        # Expected answers (if validation was performed)
        if 'expected_answers' in metadata and metadata['expected_answers']:
            info += "\n\n[bold cyan]Expected Answers:[/bold cyan]"
            for expected in metadata['expected_answers']:
                # Check if this expected answer is in the actual answers
                is_present = 'answers' in metadata and expected in metadata['answers']
                color = "green" if is_present else "red"
                icon = "✅" if is_present else "❌"
                info += f"\n• [{color}]{icon} {expected}[/{color}]"
        
        # Authoritative nameservers in verbose mode
        if self.verbose and 'authoritative_ns' in metadata and metadata['authoritative_ns']:
            info += "\n\n[bold cyan]Authoritative Nameservers:[/bold cyan]"
            for ns in metadata['authoritative_ns']:
                info += f"\n• [dim]{ns}[/dim]"
        
        return info
