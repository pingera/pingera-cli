"""
Port scan check result formatter
"""

from typing import Dict, Any, List
from .base_formatter import BaseFormatter


class PortscanFormatter(BaseFormatter):
    """Formatter for port scan check results"""

    def can_format(self, metadata: Dict[str, Any]) -> bool:
        """Check if this is portscan metadata"""
        return 'scan_results' in metadata and 'summary' in metadata

    def format(self, metadata: Dict[str, Any]) -> str:
        """Format portscan check metadata"""
        info = "\n[bold cyan]Port Scan Results:[/bold cyan]"

        # Target information
        if 'target' in metadata:
            info += f"\n• Target: [white]{metadata['target']}[/white]"

        # Execution details
        if 'execution_type' in metadata:
            info += f"\n• Execution Type: [white]{metadata['execution_type']}[/white]"
        if 'provider' in metadata:
            info += f"\n• Provider: [white]{metadata['provider']}[/white]"
        if 'region' in metadata:
            info += f"\n• Region: [white]{metadata['region']}[/white]"

        # Summary statistics
        if 'summary' in metadata:
            summary = metadata['summary']
            info += "\n\n[bold cyan]Scan Summary:[/bold cyan]"

            hosts_up = summary.get('hosts_up', 0)
            hosts_down = summary.get('hosts_down', 0)
            total_hosts = summary.get('total_hosts', 0)
            total_ports = summary.get('total_open_ports', 0)

            hosts_up_color = "green" if hosts_up > 0 else "dim"
            info += f"\n• Hosts Up: [{hosts_up_color}]{hosts_up}[/{hosts_up_color}] / [white]{total_hosts}[/white]"

            if hosts_down > 0:
                info += f"\n• Hosts Down: [red]{hosts_down}[/red]"

            ports_color = "green" if total_ports > 0 else "yellow"
            info += f"\n• Total Open Ports: [{ports_color}]{total_ports}[/{ports_color}]"

        # Scan results for each host
        if 'scan_results' in metadata and metadata['scan_results']:
            info += "\n\n[bold cyan]Host Details:[/bold cyan]"

            for host_result in metadata['scan_results']:
                hostname = host_result.get('hostname', 'Unknown')
                ip = host_result.get('ip', 'Unknown')
                state = host_result.get('state', 'unknown')

                state_color = "green" if state == 'up' else "red"
                info += f"\n\n[bold]Host:[/bold] [white]{hostname}[/white]"
                if hostname != ip:
                    info += f" ([white]{ip}[/white])"
                info += f"\n• State: [{state_color}]{state.upper()}[/{state_color}]"

                # Open ports
                open_ports = host_result.get('open_ports', [])
                if open_ports:
                    info += f"\n• Open Ports: [green]{len(open_ports)}[/green]"
                    info += self._format_open_ports(open_ports)
                else:
                    info += "\n• Open Ports: [yellow]None detected[/yellow]"

                # OS detection
                os_matches = host_result.get('os_matches', [])
                if os_matches and self.verbose:
                    info += self._format_os_matches(os_matches)

        # Vulnerabilities
        if 'vulnerabilities' in metadata:
            vulns = metadata['vulnerabilities']
            if vulns:
                info += "\n\n[bold red]Vulnerabilities:[/bold red]"
                for vuln in vulns:
                    info += f"\n• [red]{vuln}[/red]"
            elif self.verbose:
                info += "\n\n[bold green]Vulnerabilities:[/bold green]"
                info += "\n• [green]No vulnerabilities detected[/green]"

        return info

    def _format_open_ports(self, ports: List[Dict[str, Any]]) -> str:
        """Format open ports information"""
        info = ""

        for port_info in ports:
            port = port_info.get('port', '?')
            protocol = port_info.get('protocol', 'tcp')
            service = port_info.get('service', 'unknown')
            product = port_info.get('product', '')
            version = port_info.get('version', '')
            extrainfo = port_info.get('extrainfo', '')

            # Build port display
            info += f"\n  [green]•[/green] Port [cyan]{port}/{protocol}[/cyan] - [yellow]{service}[/yellow]"

            # Add product and version if available
            if product:
                info += f" ([white]{product}"
                if version:
                    info += f" {version}"
                info += "[/white])"
            elif version:
                info += f" ([white]{version}[/white])"

            # Add extra info if available and verbose
            if extrainfo and self.verbose:
                info += f"\n    [dim]{extrainfo}[/dim]"

        return info

    def _format_os_matches(self, os_matches: List[Dict[str, Any]]) -> str:
        """Format OS detection matches"""
        info = "\n• OS Detection:"

        # Show top 3 matches
        for i, os_match in enumerate(os_matches[:3]):
            name = os_match.get('name', 'Unknown OS')
            accuracy = os_match.get('accuracy', 0)

            accuracy_color = "green" if accuracy >= 90 else "yellow" if accuracy >= 70 else "dim"
            info += f"\n  [{accuracy_color}]{i+1}. {name} ({accuracy}% confidence)[/{accuracy_color}]"

        if len(os_matches) > 3:
            info += f"\n  [dim]... and {len(os_matches) - 3} more matches[/dim]"

        return info

    def _format_port_results(self, results: list) -> str:
        """Format port scan results"""
        if not results:
            return ""

        info = "\n\n[bold cyan]Port Scan Results:[/bold cyan]"

        # Group by status
        open_ports = [r for r in results if r.get('status') == 'open']
        closed_ports = [r for r in results if r.get('status') == 'closed']
        filtered_ports = [r for r in results if r.get('status') == 'filtered']

        if open_ports:
            info += "\n\n[green]Open Ports:[/green]"
            # In non-verbose mode, show first 10 open ports
            display_ports = open_ports if self.verbose else open_ports[:10]
            for port in display_ports:
                port_num = port.get('port', 'Unknown')
                service = port.get('service', 'unknown')
                info += f"\n• Port {port_num}: [green]{service}[/green]"

            if not self.verbose and len(open_ports) > 10:
                info += f"\n[dim]... and {len(open_ports) - 10} more open ports[/dim]"
                info += "\n\n[dim]💡 Some details truncated. Use --verbose flag or view full results at:[/dim]"
                info += "\n[dim]   https://app.pingera.ru (navigate to the job ID from your check execution)[/dim]"

        if closed_ports and self.verbose:
            info += f"\n\n[red]Closed Ports:[/red] {len(closed_ports)} ports"

        if filtered_ports and self.verbose:
            info += f"\n\n[yellow]Filtered Ports:[/yellow] {len(filtered_ports)} ports"

        return info

    def _get_truncation_notice(self, result_id: str) -> str:
        """
        Generates the truncation notice with a direct link to the web app
        and the command to view full results.
        """
        if result_id:
            return (
                f"[dim]💡 Some details truncated. Use --verbose flag or view full results at:[/dim]\n"
                f"[dim]   https://app.pingera.ru/checks/jobs/{result_id}[/dim]\n"
                f"[dim]   pngr checks result {result_id} --verbose[/dim]"
            )
        else:
            # Fallback if result_id is not available
            return (
                f"[dim]💡 Some details truncated. Use --verbose flag or view full results at:[/dim]\n"
                f"[dim]   https://app.pingera.ru (navigate to the job ID from your check execution)[/dim]"
            )