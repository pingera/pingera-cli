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

        # Add truncation notice at the end with result_id if available
        if not self.verbose:
            result_id = metadata.get('result_id')
            info += self._get_truncation_notice(result_id)
            info += "\n"

        return info

    def _format_headers(self, headers: Dict[str, Any]) -> str:
        """Format HTTP headers"""
        info = "\n\n[bold cyan]Response Headers:[/bold cyan]"

        # In non-verbose mode, show only security-relevant headers
        if not self.verbose:
            security_headers = [
                'content-security-policy', 'strict-transport-security',
                'x-frame-options', 'x-content-type-options',
                'content-type', 'server', 'set-cookie'
            ]
            shown_headers = 0
            for key, value in headers.items():
                if key.lower() in security_headers:
                    display_value = self._truncate_text(str(value), 80)
                    info += f"\n• {key}: [white]{display_value}[/white]"
                    shown_headers += 1

            if len(headers) > shown_headers:
                info += f"\n[dim]... and {len(headers) - shown_headers} more headers[/dim]"
        else:
            # Show all headers in verbose mode
            for key, value in headers.items():
                info += f"\n• {key}: [white]{value}[/white]"

        return info