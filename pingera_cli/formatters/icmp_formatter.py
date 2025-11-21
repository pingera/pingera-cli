
"""
ICMP (Ping) check result formatter
"""

from typing import Dict, Any
from .base_formatter import BaseFormatter


class ICMPFormatter(BaseFormatter):
    """Formatter for ICMP/Ping check results"""
    
    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this is ICMP metadata"""
        return 'packet_loss_percent' in metadata or 'latency_avg_ms' in metadata
    
    def format(self, metadata: Dict[str, Any]) -> str:
        """Format ICMP check metadata"""
        info = "\n[bold cyan]ICMP Ping Results:[/bold cyan]"
        
        # Host and IP information
        if 'original_host' in metadata:
            info += f"\n• Target Host: [white]{metadata['original_host']}[/white]"
        if 'resolved_ip' in metadata:
            info += f"\n• Resolved IP: [white]{metadata['resolved_ip']}[/white]"
        if 'ip_version_used' in metadata:
            info += f"\n• IP Version: [white]{metadata['ip_version_used']}[/white]"
        
        # Packet loss
        if 'packet_loss_percent' in metadata:
            loss = metadata['packet_loss_percent']
            loss_color = "green" if loss == 0 else "yellow" if loss < 25 else "red"
            info += f"\n• Packet Loss: [{loss_color}]{loss}%[/{loss_color}]"
        
        # Latency statistics
        if 'latency_avg_ms' in metadata:
            info += f"\n• Average Latency: [yellow]{metadata['latency_avg_ms']:.3f}ms[/yellow]"
        if 'latency_min_ms' in metadata:
            info += f"\n• Min Latency: [green]{metadata['latency_min_ms']:.3f}ms[/green]"
        if 'latency_max_ms' in metadata:
            info += f"\n• Max Latency: [red]{metadata['latency_max_ms']:.3f}ms[/red]"
        if 'latency_stddev_ms' in metadata:
            info += f"\n• Std Deviation: [white]{metadata['latency_stddev_ms']:.3f}ms[/white]"
        
        # Probe configuration
        if 'probe_count' in metadata:
            info += f"\n• Probes Sent: [white]{metadata['probe_count']}[/white]"
        if 'probe_interval_seconds' in metadata:
            info += f"\n• Probe Interval: [white]{metadata['probe_interval_seconds']}s[/white]"
        if 'probe_timeout_seconds' in metadata:
            info += f"\n• Probe Timeout: [white]{metadata['probe_timeout_seconds']}s[/white]"
        
        # Individual latencies in verbose mode
        if self.verbose and 'latencies_ms' in metadata and metadata['latencies_ms']:
            info += "\n\n[bold cyan]Individual Probe Latencies:[/bold cyan]"
            for i, latency in enumerate(metadata['latencies_ms'], 1):
                info += f"\n• Probe {i}: [yellow]{latency:.3f}ms[/yellow]"
        
        # Raw ping output in verbose mode
        if self.verbose and 'raw_ping_output' in metadata:
            info += "\n\n[bold cyan]Raw Ping Output:[/bold cyan]"
            info += f"\n[dim]{metadata['raw_ping_output']}[/dim]"
        
        return info
