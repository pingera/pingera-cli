
"""
Web check result formatter
"""

from typing import Dict, Any
from .base_formatter import BaseFormatter


class WebFormatter(BaseFormatter):
    """Formatter for web check results"""
    
    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this is web metadata"""
        return 'headers' in metadata or 'status_code' in metadata
    
    def format(self, metadata: Dict[str, Any]) -> str:
        """Format web check metadata"""
        info = "\n[bold cyan]Web Check Results:[/bold cyan]"
        
        # HTTP Response
        if 'status_code' in metadata:
            code = metadata['status_code']
            if 200 <= code < 300:
                info += f"\n• Status Code: [green]{code}[/green]"
            elif 400 <= code < 500:
                info += f"\n• Status Code: [yellow]{code}[/yellow]"
            else:
                info += f"\n• Status Code: [red]{code}[/red]"
        
        # IP and Location
        if 'ip_address' in metadata:
            info += f"\n• IP Address: [white]{metadata['ip_address']}[/white]"
        if 'region' in metadata:
            info += f"\n• Region: [white]{metadata['region']}[/white]"
        if 'provider' in metadata:
            info += f"\n• Provider: [white]{metadata['provider']}[/white]"
        
        # SSL Certificate Info
        if 'ssl_cert_expiration' in metadata:
            info += f"\n• SSL Expires: [white]{metadata['ssl_cert_expiration']}[/white]"
            if 'ssl_cert_expiration_seconds' in metadata:
                days = metadata['ssl_cert_expiration_seconds'] // 86400
                color = "green" if days > 30 else "yellow" if days > 7 else "red"
                info += f" ([{color}]{days} days remaining[/{color}])"
        
        # Response Headers
        if 'headers' in metadata:
            info += self._format_headers(metadata['headers'])
        
        return info
    
    def _format_headers(self, headers: Dict[str, Any]) -> str:
        """Format response headers"""
        info = "\n\n[bold cyan]Response Headers:[/bold cyan]"
        
        if self.verbose:
            # In verbose mode, show ALL headers
            for header, value in headers.items():
                info += f"\n• {header.title()}: [dim]{value}[/dim]"
        else:
            # In non-verbose mode, show important headers only
            important_headers = [
                'content-type', 'content-length', 'server', 'cache-control', 
                'x-frame-options', 'strict-transport-security', 'x-content-type-options'
            ]
            
            for header in important_headers:
                if header in headers:
                    value = self._truncate_text(headers[header])
                    info += f"\n• {header.title()}: [dim]{value}[/dim]"
            
            # Count other headers
            other_count = len(headers) - len([h for h in important_headers if h in headers])
            if other_count > 0:
                info += f"\n• [dim]... and {other_count} more headers (use --verbose to see all)[/dim]"
        
        return info
