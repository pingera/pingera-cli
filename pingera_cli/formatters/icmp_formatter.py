"""
ICMP check result formatter
"""

from typing import Dict, Any
from .base_formatter import BaseFormatter


class IcmpFormatter(BaseFormatter):
    """Formatter for ICMP check results"""

    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this is ICMP metadata"""
        return 'packet_loss' in metadata or 'avg_rtt' in metadata

    def format(self, metadata: Dict[str, Any]) -> str:
        """Format ICMP check metadata"""
        info = "\n[bold cyan]ICMP Ping Results:[/bold cyan]"

        # Packet statistics
        if 'packets_sent' in metadata:
            info += f"\n• Packets Sent: [white]{metadata['packets_sent']}[/white]"
        if 'packets_received' in metadata:
            info += f"\n• Packets Received: [white]{metadata['packets_received']}[/white]"
        if 'packet_loss' in metadata:
            loss = metadata['packet_loss']
            loss_color = "green" if loss == 0 else "yellow" if loss < 50 else "red"
            info += f"\n• Packet Loss: [{loss_color}]{loss}%[/{loss_color}]"

        # RTT statistics
        if 'min_rtt' in metadata:
            info += f"\n• Min RTT: [green]{metadata['min_rtt']:.2f}ms[/green]"
        if 'avg_rtt' in metadata:
            info += f"\n• Avg RTT: [yellow]{metadata['avg_rtt']:.2f}ms[/yellow]"
        if 'max_rtt' in metadata:
            info += f"\n• Max RTT: [red]{metadata['max_rtt']:.2f}ms[/red]"
        if 'stddev_rtt' in metadata:
            info += f"\n• Std Dev: [white]{metadata['stddev_rtt']:.2f}ms[/white]"

        return info