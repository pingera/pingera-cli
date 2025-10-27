
"""
Execution groups commands for PingeraCLI
"""

from typing import Optional

import typer
from rich.table import Table
from rich.panel import Panel

from .base import BaseCommand
from ..utils.config import get_api_key


class ExecutionGroupsCommand(BaseCommand):
    """
    Commands for managing check execution groups
    """

    def __init__(self, output_format: Optional[str] = None):
        super().__init__(output_format)

    def get_client(self):
        """Get Pingera SDK client with authentication for execution groups"""
        api_key = get_api_key()
        if not api_key:
            self.display_error("API key not found. Use 'pngr auth login --api-key <key>' to set it.")
            raise typer.Exit(1)

        try:
            from pingera import ApiClient, Configuration
            from pingera.api import ExecutionGroupsApi
            from ..utils.config import get_config

            # Configure the client
            configuration = Configuration()
            configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return ExecutionGroupsApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def list_execution_groups(self, check_id: str, page: int = 1, page_size: int = 20):
        """List execution groups for a specific check"""
        try:
            groups_api = self.get_client()

            # Get execution groups for check
            response = groups_api.v1_checks_check_id_execution_groups_get(
                check_id=check_id,
                page=page,
                page_size=page_size
            )

            if not hasattr(response, 'execution_groups') or not response.execution_groups:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({"execution_groups": [], "total": 0, "message": "No execution groups found"})
                else:
                    self.display_info("No execution groups found.")
                return

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                groups_data = []
                for group in response.execution_groups:
                    # Calculate region counts from requested_regions and regional_summary
                    total_regions = len(group.requested_regions) if hasattr(group, 'requested_regions') and group.requested_regions else 0
                    successful_regions = 0
                    failed_regions = 0
                    completed_regions = 0
                    if hasattr(group, 'regional_summary') and group.regional_summary:
                        for region, data in group.regional_summary.items():
                            if isinstance(data, dict):
                                completed_regions += 1
                                if data.get('status') == 'ok':
                                    successful_regions += 1
                                else:
                                    failed_regions += 1
                    
                    group_dict = {
                        "id": str(group.id) if hasattr(group, 'id') and group.id else None,
                        "check_id": group.check_id if hasattr(group, 'check_id') else None,
                        "created_at": group.created_at.isoformat() if hasattr(group, 'created_at') and group.created_at else None,
                        "status": group.status if hasattr(group, 'status') else None,
                        "requested_regions": group.requested_regions if hasattr(group, 'requested_regions') else [],
                        "statistics": {
                            "total_regions": total_regions,
                            "completed_regions": completed_regions,
                            "successful_regions": successful_regions,
                            "failed_regions": failed_regions,
                            "avg_response_time": group.statistics.avg_response_time if hasattr(group, 'statistics') and group.statistics and hasattr(group.statistics, 'avg_response_time') else None,
                            "min_response_time": group.statistics.min_response_time if hasattr(group, 'statistics') and group.statistics and hasattr(group.statistics, 'min_response_time') else None,
                            "max_response_time": group.statistics.max_response_time if hasattr(group, 'statistics') and group.statistics and hasattr(group.statistics, 'max_response_time') else None
                        }
                    }
                    groups_data.append(group_dict)

                self.output_data({
                    "execution_groups": groups_data,
                    "check_id": check_id,
                    "total": len(groups_data),
                    "page": page,
                    "page_size": page_size
                })
            else:
                # Create table for default output
                table = Table(title=f"Execution Groups for Check {check_id}")
                table.add_column("Group ID", style="cyan", min_width=15)
                table.add_column("Created", style="dim")
                table.add_column("Status", style="magenta")
                table.add_column("Regions", style="white")
                table.add_column("Success Rate", style="green")
                table.add_column("Avg Response", style="yellow")

                for group in response.execution_groups:
                    group_id = str(group.id) if hasattr(group, 'id') and group.id else "-"
                    created = group.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(group, 'created_at') and group.created_at else "-"
                    
                    # Status with color
                    status = group.status if hasattr(group, 'status') and group.status else "unknown"
                    status_color = "green" if status == "completed" else "yellow" if status == "running" else "red"
                    status_display = f"[{status_color}]{status}[/{status_color}]"
                    
                    # Regions progress - use requested_regions instead
                    regions_display = "-"
                    if hasattr(group, 'requested_regions') and group.requested_regions:
                        total = len(group.requested_regions)
                        # Check if execution is completed to determine completed count
                        completed = total if (hasattr(group, 'status') and group.status == 'completed') else 0
                        regions_display = f"{completed}/{total}"
                    
                    # Success rate - calculate from regional_summary if available
                    success_rate_display = "-"
                    if hasattr(group, 'requested_regions') and group.requested_regions:
                        total = len(group.requested_regions)
                        # Try to get success count from regional_summary
                        successful = 0
                        if hasattr(group, 'regional_summary') and group.regional_summary:
                            successful = sum(1 for region, data in group.regional_summary.items() 
                                           if isinstance(data, dict) and data.get('status') == 'ok')
                        if total > 0 and successful > 0:
                            rate = (successful / total) * 100
                            color = "green" if rate >= 80 else "yellow" if rate >= 50 else "red"
                            success_rate_display = f"[{color}]{rate:.1f}%[/{color}]"
                    
                    # Average response time
                    avg_response_display = "-"
                    if hasattr(group, 'statistics') and group.statistics and hasattr(group.statistics, 'avg_response_time') and group.statistics.avg_response_time is not None:
                        avg_response_display = f"{group.statistics.avg_response_time:.0f}ms"

                    table.add_row(
                        group_id,
                        created,
                        status_display,
                        regions_display,
                        success_rate_display,
                        avg_response_display
                    )

                self.console.print(table)
                self.console.print(f"\n[dim]Found {len(response.execution_groups)} execution groups for check {check_id}[/dim]")
                self.console.print(f"[dim]💡 Use 'pngr checks execution-groups get <group-id>' for detailed group information[/dim]")

        except Exception as e:
            self.display_error(f"Failed to list execution groups: {str(e)}")
            raise typer.Exit(1)

    def get_execution_group(self, group_id: str):
        """Get specific execution group details"""
        try:
            groups_api = self.get_client()
            group = groups_api.v1_execution_groups_group_id_get(group_id=group_id)

            if self.output_format in ['json', 'yaml']:
                # Calculate region counts from requested_regions and regional_summary
                total_regions = len(group.requested_regions) if hasattr(group, 'requested_regions') and group.requested_regions else 0
                successful_regions = 0
                failed_regions = 0
                completed_regions = 0
                if hasattr(group, 'regional_summary') and group.regional_summary:
                    for region, data in group.regional_summary.items():
                        if isinstance(data, dict):
                            completed_regions += 1
                            if data.get('status') == 'ok':
                                successful_regions += 1
                            else:
                                failed_regions += 1
                
                group_data = {
                    "id": str(group.id) if hasattr(group, 'id') and group.id else None,
                    "check_id": group.check_id if hasattr(group, 'check_id') else None,
                    "created_at": group.created_at.isoformat() if hasattr(group, 'created_at') and group.created_at else None,
                    "completed_at": group.completed_at.isoformat() if hasattr(group, 'completed_at') and group.completed_at else None,
                    "status": group.status if hasattr(group, 'status') else None,
                    "requested_regions": group.requested_regions if hasattr(group, 'requested_regions') else [],
                    "regional_summary": group.regional_summary if hasattr(group, 'regional_summary') else None,
                    "statistics": {
                        "total_regions": total_regions,
                        "completed_regions": completed_regions,
                        "successful_regions": successful_regions,
                        "failed_regions": failed_regions,
                        "avg_response_time": group.statistics.avg_response_time if hasattr(group, 'statistics') and group.statistics and hasattr(group.statistics, 'avg_response_time') else None,
                        "min_response_time": group.statistics.min_response_time if hasattr(group, 'statistics') and group.statistics and hasattr(group.statistics, 'min_response_time') else None,
                        "max_response_time": group.statistics.max_response_time if hasattr(group, 'statistics') and group.statistics and hasattr(group.statistics, 'max_response_time') else None
                    }
                }
                self.output_data(group_data)
            else:
                # Rich formatted output
                status_color = "green" if hasattr(group, 'status') and group.status == "completed" else "yellow" if hasattr(group, 'status') and group.status == "running" else "red"
                
                basic_info = f"""[bold cyan]Execution Group Information:[/bold cyan]
• Group ID: [white]{group.id}[/white]
• Check ID: [white]{group.check_id}[/white]
• Status: [{status_color}]{group.status if hasattr(group, 'status') else 'unknown'}[/{status_color}]
• Created: [white]{group.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(group, 'created_at') and group.created_at else 'Unknown'}[/white]
• Completed: [white]{group.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(group, 'completed_at') and group.completed_at else 'Not completed'}[/white]"""

                stats_info = ""
                
                # Calculate regional stats from requested_regions and regional_summary
                if hasattr(group, 'requested_regions') and group.requested_regions:
                    total_regions = len(group.requested_regions)
                    successful_regions = 0
                    failed_regions = 0
                    completed_regions = 0
                    
                    # Parse regional_summary to get actual counts
                    if hasattr(group, 'regional_summary') and group.regional_summary:
                        for region, data in group.regional_summary.items():
                            if isinstance(data, dict):
                                completed_regions += 1
                                if data.get('status') == 'ok':
                                    successful_regions += 1
                                else:
                                    failed_regions += 1
                    
                    success_rate = (successful_regions / total_regions * 100) if total_regions > 0 else 0
                    success_color = "green" if success_rate >= 80 else "yellow" if success_rate >= 50 else "red"
                    
                    stats_info = f"""
[bold cyan]Statistics:[/bold cyan]
• Total Regions: [white]{total_regions}[/white]
• Completed: [white]{completed_regions}[/white]
• Successful: [green]{successful_regions}[/green]
• Failed: [red]{failed_regions}[/red]
• Success Rate: [{success_color}]{success_rate:.1f}%[/{success_color}]"""
                
                # Add response time stats if available from statistics object
                if hasattr(group, 'statistics') and group.statistics:
                    stats = group.statistics
                    
                    if hasattr(stats, 'avg_response_time') and stats.avg_response_time is not None:
                        avg_resp = stats.avg_response_time
                        min_resp = stats.min_response_time if hasattr(stats, 'min_response_time') and stats.min_response_time is not None else avg_resp
                        max_resp = stats.max_response_time if hasattr(stats, 'max_response_time') and stats.max_response_time is not None else avg_resp
                        
                        stats_info += f"""
• Avg Response Time: [yellow]{avg_resp:.0f}ms[/yellow]
• Min Response Time: [green]{min_resp:.0f}ms[/green]
• Max Response Time: [red]{max_resp:.0f}ms[/red]"""

                full_info = basic_info
                if stats_info:
                    full_info += stats_info

                panel = Panel(
                    full_info,
                    title=f"🔍 Execution Group Details: {group.id}",
                    border_style="blue",
                    padding=(1, 2),
                )

                self.console.print(panel)
                self.console.print(f"\n[dim]💡 Use 'pngr checks execution-groups regional-results {group.id}' to see regional breakdown[/dim]")

        except Exception as e:
            self.display_error(f"Failed to get execution group: {str(e)}")
            raise typer.Exit(1)

    def get_regional_results(self, group_id: str, page: int = 1, page_size: int = 20):
        """Get regional results for an execution group"""
        try:
            groups_api = self.get_client()

            response = groups_api.v1_execution_groups_group_id_regional_results_get(group_id=group_id)

            if not hasattr(response, 'regional_results') or not response.regional_results:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({"regional_results": [], "total": 0, "message": "No regional results found"})
                else:
                    self.display_info("No regional results found.")
                return

            if self.output_format in ['json', 'yaml']:
                results_data = []
                for result in response.regional_results:
                    result_dict = {
                        "id": str(result.id) if hasattr(result, 'id') and result.id else None,
                        "execution_group_id": result.execution_group_id if hasattr(result, 'execution_group_id') else None,
                        "region": result.region if hasattr(result, 'region') else None,
                        "status": result.status if hasattr(result, 'status') else None,
                        "response_time": result.response_time if hasattr(result, 'response_time') else None,
                        "created_at": result.created_at.isoformat() if hasattr(result, 'created_at') and result.created_at else None,
                        "error_message": result.error_message if hasattr(result, 'error_message') else None,
                        "check_server": {
                            "ip_address": result.check_server.ip_address if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'ip_address') else None,
                            "country": result.check_server.country if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'country') else None,
                            "region": result.check_server.region if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'region') else None
                        } if hasattr(result, 'check_server') and result.check_server else None
                    }
                    results_data.append(result_dict)

                self.output_data({
                    "regional_results": results_data,
                    "execution_group_id": group_id,
                    "total": len(results_data),
                    "page": page,
                    "page_size": page_size
                })
            else:
                table = Table(title=f"Regional Results for Execution Group {group_id}")
                table.add_column("Result ID", style="dim", min_width=15)
                table.add_column("Region", style="cyan")
                table.add_column("Status", style="magenta")
                table.add_column("Response Time", style="yellow")
                table.add_column("Server IP", style="white")
                table.add_column("Error", style="red", max_width=30)

                for result in response.regional_results:
                    result_id = str(result.id) if hasattr(result, 'id') and result.id else "-"
                    region = result.region if hasattr(result, 'region') and result.region else "-"
                    
                    # Status with color
                    status = result.status if hasattr(result, 'status') and result.status else "unknown"
                    status_color = "green" if status == "ok" else "red"
                    status_emoji = "✅" if status == "ok" else "❌"
                    status_display = f"[{status_color}]{status_emoji} {status}[/{status_color}]"
                    
                    # Response time - handle <1ms case
                    response_time_display = "-"
                    if hasattr(result, 'response_time') and result.response_time is not None:
                        if result.response_time == 0:
                            response_time_display = "<1ms"
                        else:
                            response_time_display = f"{result.response_time}ms"
                    
                    # Server IP
                    server_ip = "-"
                    if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'ip_address'):
                        server_ip = result.check_server.ip_address
                    
                    # Error message
                    error_msg = "-"
                    if hasattr(result, 'error_message') and result.error_message:
                        error_msg = result.error_message
                        if len(error_msg) > 29:
                            error_msg = error_msg[:29] + "…"

                    table.add_row(
                        result_id,
                        region,
                        status_display,
                        response_time_display,
                        server_ip,
                        error_msg
                    )

                self.console.print(table)
                self.console.print(f"\n[dim]Found {len(response.regional_results)} regional results[/dim]")

        except Exception as e:
            self.display_error(f"Failed to get regional results: {str(e)}")
            raise typer.Exit(1)


# Create Typer app for execution groups commands
app = typer.Typer(name="execution-groups", help="🌍 Manage execution groups")


def get_output_format():
    """Get output format from config"""
    from ..utils.config import get_config
    return get_config().get('output_format', 'table')


@app.command("list")
def list_execution_groups(
    check_id: str = typer.Argument(..., help="Check ID to list execution groups for"),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Items per page"),
):
    """List execution groups for a specific check"""
    exec_groups_cmd = ExecutionGroupsCommand(get_output_format())
    exec_groups_cmd.list_execution_groups(check_id, page, page_size)


@app.command("get")
def get_execution_group(
    group_id: str = typer.Argument(..., help="Execution group ID to retrieve"),
):
    """Get specific execution group details with statistics"""
    exec_groups_cmd = ExecutionGroupsCommand(get_output_format())
    exec_groups_cmd.get_execution_group(group_id)


@app.command("regional-results")
def get_regional_results(
    group_id: str = typer.Argument(..., help="Execution group ID to get regional results for"),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Items per page"),
):
    """Get regional results breakdown for an execution group"""
    exec_groups_cmd = ExecutionGroupsCommand(get_output_format())
    exec_groups_cmd.get_regional_results(group_id, page, page_size)
