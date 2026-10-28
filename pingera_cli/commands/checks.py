"""
Checks commands for PingeraCLI
"""

import os
from typing import Optional, List
from datetime import datetime

import typer
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from .base import BaseCommand, to_plain
from ..utils.time_utils import parse_time_arg
from ..utils.config import get_api_key

# Supported check types
SUPPORTED_CHECK_TYPES = ["web", "api", "tcp", "ssl", "dns", "icmp", "portscan", "synthetic", "multistep"]


def _format_schedule(check) -> str:
    """Human-readable schedule for interval- and cron-scheduled checks."""
    if getattr(check, 'scheduling_type', None) == 'cron':
        return f"cron '{check.cron_schedule}'"
    if getattr(check, 'interval', None):
        return f"every {check.interval}s"
    return "-"


class ChecksCommand(BaseCommand):
    """
    Commands for managing monitoring checks
    """

    def __init__(self, output_format: Optional[str] = None):
        super().__init__(output_format)

    def get_client(self):
        """Get Pingera SDK client with authentication"""
        api_key = get_api_key()
        if not api_key:
            self.display_error("API key not found. Use 'pngr auth login --api-key <key>' to set it.")
            raise typer.Exit(1)

        try:
            from pingera import ApiClient, Configuration
            from pingera.api import ChecksApi
            from ..utils.config import get_config

            # Configure the client
            configuration = Configuration()
            configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return ChecksApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def get_unified_results_client(self):
        """Get Pingera SDK client for unified results with authentication"""
        api_key = get_api_key()
        if not api_key:
            self.display_error("API key not found. Use 'pngr auth login --api-key <key>' to set it.")
            raise typer.Exit(1)

        try:
            from pingera import ApiClient, Configuration
            from pingera.api import ChecksUnifiedResultsApi
            from ..utils.config import get_config

            # Configure the client
            configuration = Configuration()
            configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return ChecksUnifiedResultsApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def list_checks(self, page: int = 1, page_size: int = 20, check_type: Optional[str] = None, status: Optional[str] = None, name: Optional[str] = None, group_id: Optional[str] = None):
        """List monitoring checks"""
        try:
            checks_api = self.get_client()

            # Build parameters for the API call
            params = {
                "page": page,
                "page_size": page_size
            }

            # Add optional filters
            if check_type:
                params["type"] = check_type
            if status:
                params["status"] = status
            if name:
                params["name"] = name
            if group_id:
                params["group_id"] = group_id

            # Make API call using the actual SDK method with filters
            response = checks_api.v1_checks_get(**params)

            if not response.checks:
                if self.output_format == 'json':
                    self.output_data({"checks": [], "total": 0, "message": "No checks found"})
                elif self.output_format == 'yaml':
                    self.output_data({"checks": [], "total": 0, "message": "No checks found"})
                else:
                    self.display_info("No checks found.")
                return

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                checks_data = []
                for check in response.checks:
                    check_dict = {
                        "id": str(check.id) if check.id else None,
                        "name": check.name if check.name else None,
                        "type": check.type if check.type else None,
                        "url": check.url if check.url else None,
                        "status": check.status if check.status else None,
                        "interval": check.interval if check.interval else None,
                        "scheduling_type": getattr(check, 'scheduling_type', None),
                        "cron_schedule": getattr(check, 'cron_schedule', None),
                        "created_at": check.created_at.isoformat() if hasattr(check, 'created_at') and check.created_at else None,
                        "group_id": check.group_id if hasattr(check, 'group_id') else None,
                        "group": {
                            "id": check.group.id if hasattr(check, 'group') and check.group and hasattr(check.group, 'id') else None,
                            "name": check.group.name if hasattr(check, 'group') and check.group and hasattr(check.group, 'name') else None,
                            "color": check.group.color if hasattr(check, 'group') and check.group and hasattr(check.group, 'color') else None,
                            "description": check.group.description if hasattr(check, 'group') and check.group and hasattr(check.group, 'description') else None
                        } if hasattr(check, 'group') and check.group else None
                    }
                    checks_data.append(check_dict)

                self.output_data({
                    "checks": checks_data,
                    "total": len(checks_data),
                    "page": page,
                    "page_size": page_size
                })
            else:
                # Build title with applied filters
                title_parts = ["Monitoring Checks"]
                filters_applied = []
                if check_type:
                    filters_applied.append(f"type={check_type}")
                if status:
                    filters_applied.append(f"status={status}")
                if name:
                    filters_applied.append(f"name='{name}'")
                if group_id:
                    filters_applied.append(f"group={group_id}")

                if filters_applied:
                    title_parts.append(f"({', '.join(filters_applied)})")

                table_title = " ".join(title_parts)

                # Create table for default output
                table = Table(title=table_title)
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Group", style="magenta", max_width=20)
                table.add_column("Type", style="blue")
                table.add_column("URL", style="yellow")
                table.add_column("Active", style="magenta")
                table.add_column("Schedule", style="white")
                table.add_column("Status", style="white")
                table.add_column("Created", style="dim")

                for check in response.checks:
                    # Convert all values to strings to avoid Rich rendering issues
                    check_id = str(check.id) if hasattr(check, 'id') and check.id else "-"
                    check_name = str(check.name) if hasattr(check, 'name') and check.name else "-"
                    check_type = str(check.type) if hasattr(check, 'type') and check.type else "-"

                    # Handle group display
                    group_display = "-"
                    if hasattr(check, 'group') and check.group and hasattr(check.group, 'name'):
                        group_name = str(check.group.name)
                        # Truncate long group names
                        if len(group_name) > 19:
                            group_display = group_name[:19] + "…"
                        else:
                            group_display = group_name

                        # Add color if available
                        if hasattr(check.group, 'color') and check.group.color:
                            # Use the group color for the group name display
                            group_display = f"[{check.group.color}]●[/{check.group.color}] {group_display}"
                    elif hasattr(check, 'group_id') and check.group_id:
                        # If we have group_id but no group object, show the ID
                        group_display = f"[dim]{check.group_id}[/dim]"

                    # Handle URL/Host display
                    check_url = "-"
                    if hasattr(check, 'url') and check.url:
                        check_url = str(check.url)
                    elif hasattr(check, 'host') and check.host:
                        # For ICMP and DNS checks, show just the host
                        # For TCP and other checks with ports, show host:port
                        if check_type in ["icmp", "dns"]:
                            check_url = str(check.host)
                        elif hasattr(check, 'port') and check.port:
                            check_url = f"{check.host}:{check.port}"
                        else:
                            check_url = str(check.host)

                    # Handle active status
                    active_status = "✅" if hasattr(check, 'active') and check.active else "❌"

                    # Handle interval
                    if getattr(check, 'scheduling_type', None) == 'cron':
                        interval_display = f"cron {check.cron_schedule}"
                    else:
                        interval_display = f"{check.interval}s" if hasattr(check, 'interval') and check.interval else "-"

                    # Handle status
                    status_display = str(check.status) if hasattr(check, 'status') and check.status else "-"

                    # Handle created_at
                    created_display = "-"
                    if hasattr(check, 'created_at') and check.created_at:
                        try:
                            created_display = check.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        except (AttributeError, TypeError):
                            created_display = str(check.created_at)

                    table.add_row(
                        check_id,
                        check_name,
                        group_display,
                        check_type,
                        check_url,
                        active_status,
                        interval_display,
                        status_display,
                        created_display
                    )

                self.console.print(table)

                # Show result summary with filter info
                summary_parts = [f"Found {len(response.checks)} checks"]
                if page > 1:
                    summary_parts.append(f"on page {page}")
                if filters_applied:
                    summary_parts.append(f"with filters: {', '.join(filters_applied)}")

                self.console.print(f"\n[dim]{' '.join(summary_parts)}[/dim]")

                # Show helpful hints for filtering
                if not any([check_type, status, name, group_id]):
                    self.console.print(f"[dim]💡 Filter checks: --type <type>, --status <status>, --name <name>, --group-id <id>[/dim]")
                    self.console.print(f"[dim]💡 Multiple statuses: --status 'ok,failed'[/dim]")

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to list checks: {str(e)}")
            raise typer.Exit(1)

    def get_check(self, check_id: str):
        """Get specific check details"""
        try:
            checks_api = self.get_client()
            check = checks_api.v1_checks_check_id_get(check_id=check_id)

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                check_data = {
                    "id": str(check.id) if check.id else None,
                    "name": check.name if check.name else None,
                    "type": check.type if check.type else None,
                    "status": check.status if check.status else None,
                    "active": check.active if hasattr(check, 'active') else None,
                    "url": check.url if check.url else None,
                    "host": check.host if hasattr(check, 'host') and check.host else None,
                    "port": check.port if hasattr(check, 'port') and check.port else None,
                    "interval": check.interval if check.interval else None,
                    "scheduling_type": getattr(check, 'scheduling_type', None),
                    "cron_schedule": getattr(check, 'cron_schedule', None),
                    "effective_interval": getattr(check, 'effective_interval', None),
                    "credit_throttled": getattr(check, 'credit_throttled', None),
                    "timeout": check.timeout if check.timeout else None,
                    "created_at": check.created_at.isoformat() if hasattr(check, 'created_at') and check.created_at else None,
                    "updated_at": check.updated_at.isoformat() if hasattr(check, 'updated_at') and check.updated_at else None,
                    "last_checked_at": check.last_checked_at.isoformat() if hasattr(check, 'last_checked_at') and check.last_checked_at else None,
                    "parameters": check.parameters if hasattr(check, 'parameters') and check.parameters else None,
                    "group_id": check.group_id if hasattr(check, 'group_id') else None,
                    "group": {
                        "id": check.group.id if hasattr(check, 'group') and check.group and hasattr(check.group, 'id') else None,
                        "name": check.group.name if hasattr(check, 'group') and check.group and hasattr(check.group, 'name') else None,
                        "color": check.group.color if hasattr(check, 'group') and check.group and hasattr(check.group, 'color') else None,
                        "description": check.group.description if hasattr(check, 'group') and check.group and hasattr(check.group, 'description') else None,
                        "position": check.group.position if hasattr(check, 'group') and check.group and hasattr(check.group, 'position') else None,
                        "active": check.group.active if hasattr(check, 'group') and check.group and hasattr(check.group, 'active') else None,
                        "created_at": check.group.created_at.isoformat() if hasattr(check, 'group') and check.group and hasattr(check.group, 'created_at') and check.group.created_at else None,
                        "updated_at": check.group.updated_at.isoformat() if hasattr(check, 'group') and check.group and hasattr(check.group, 'updated_at') and check.group.updated_at else None
                    } if hasattr(check, 'group') and check.group else None
                }
                self.output_data(check_data)
            else:
                # Rich formatted output for table format
                status_color = "green" if check.status == "ok" else "red" if check.status == "error" else "yellow"
                active_status = "[green]✓ Active[/green]" if check.active else "[red]✗ Inactive[/red]"

                # Handle group information
                group_info = ""
                if hasattr(check, 'group') and check.group:
                    group_name = check.group.name if hasattr(check.group, 'name') else 'Unknown'
                    group_color = check.group.color if hasattr(check.group, 'color') and check.group.color else 'white'
                    group_desc = check.group.description if hasattr(check.group, 'description') and check.group.description else ''

                    group_info = f"• Group: [{group_color}]● {group_name}[/{group_color}]"
                    if group_desc:
                        group_info += f" [dim]({group_desc})[/dim]"
                    group_info += "\n"
                elif hasattr(check, 'group_id') and check.group_id:
                    group_info = f"• Group ID: [white]{check.group_id}[/white]\n"

                basic_info = f"""[bold cyan]Basic Information:[/bold cyan]
• ID: [white]{check.id}[/white]
• Name: [white]{check.name}[/white]
{group_info}• Type: [blue]{check.type}[/blue]
• Status: [{status_color}]{check.status}[/{status_color}]
• Active: {active_status}
• URL: [yellow]{check.url if check.url else 'N/A'}[/yellow]
• Host: [white]{check.host if hasattr(check, 'host') and check.host else 'N/A'}[/white]
• Port: [white]{check.port if hasattr(check, 'port') and check.port else 'N/A'}[/white]"""

                # Timing information
                timing_info = f"""[bold cyan]Timing & Monitoring:[/bold cyan]
• Schedule: [white]{_format_schedule(check)}[/white]{f" ({check.interval // 60} minutes)" if getattr(check, 'scheduling_type', None) != 'cron' and check.interval else ""}{" [yellow](throttled: low credits)[/yellow]" if getattr(check, 'credit_throttled', False) else ""}
• Timeout: [white]{check.timeout}s[/white]
• Created: [white]{check.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if check.created_at else 'Unknown'}[/white]
• Updated: [white]{check.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(check, 'updated_at') and check.updated_at else 'Unknown'}[/white]
• Last Checked: [white]{check.last_checked_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(check, 'last_checked_at') and check.last_checked_at else 'Never'}[/white]"""

                # Parameters section
                parameters_info = "[bold cyan]Parameters:[/bold cyan]\n"
                if hasattr(check, 'parameters') and check.parameters:
                    params = check.parameters

                    # Handle different check types
                    if check.type == 'web' or check.type == 'api':
                        if 'http_request' in params:
                            http_req = params['http_request']
                            parameters_info += f"• Method: [white]{http_req.get('method', 'GET')}[/white]\n"
                            if http_req.get('headers'):
                                parameters_info += "• Headers:\n"
                                for key, value in http_req['headers'].items():
                                    # Mask sensitive headers
                                    if key.lower() in ['authorization', 'x-api-key', 'token']:
                                        value = "***" + value[-4:] if len(value) > 4 else "***"
                                    parameters_info += f"  - {key}: [dim]{value}[/dim]\n"
                            if http_req.get('body'):
                                # Show more of the body content, only truncate if very long
                                if len(http_req['body']) > 500:
                                    body_preview = http_req['body'][:500] + "..."
                                else:
                                    body_preview = http_req['body']
                                parameters_info += f"• Body: [dim]{body_preview}[/dim]\n"
                            if http_req.get('username'):
                                parameters_info += f"• Username: [white]{http_req['username']}[/white]\n"

                        if 'search_text' in params and params['search_text']:
                            parameters_info += f"• Search Text: [white]{params['search_text']}[/white]\n"

                        if 'regions' in params:
                            parameters_info += f"• Regions: [white]{', '.join(params['regions'])}[/white]\n"

                    elif check.type == 'multistep' or check.type == 'synthetic':
                        if 'pw_script' in params:
                            # Display full script without truncation
                            parameters_info += f"• Playwright Script:\n[dim]{params['pw_script']}[/dim]\n"
                        if 'regions' in params:
                            parameters_info += f"• Regions: [white]{', '.join(params['regions'])}[/white]\n"

                    elif check.type == 'ssl':
                        if 'assertions' in params:
                            assertions = params['assertions']
                            if 'expiration_threshold' in assertions:
                                days = assertions['expiration_threshold'] // 86400
                                parameters_info += f"• Expiration Threshold: [white]{days} days[/white]\n"

                    # Show any other parameters
                    for key, value in params.items():
                        if key not in ['http_request', 'search_text', 'regions', 'pw_script', 'assertions']:
                            parameters_info += f"• {key.replace('_', ' ').title()}: [white]{value}[/white]\n"
                else:
                    parameters_info += "• [dim]No parameters configured[/dim]"

                # Combine all sections
                full_info = f"{basic_info}\n\n{timing_info}\n\n{parameters_info}"

                panel = Panel(
                    full_info,
                    title=f"🔍 Check Details: {check.name}",
                    border_style="blue",
                    padding=(1, 2),
                )

                self.console.print(panel)

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to get check: {str(e)}")
            raise typer.Exit(1)

    def _parse_check_file(self, file_path: str) -> dict:
        """Parse check configuration from JSON or YAML file (local or URL)"""
        from ..utils.file_utils import load_check_file, is_url

        try:
            if is_url(file_path):
                self.display_info(f"Downloading check configuration from: {file_path}")

            return load_check_file(file_path)

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(str(e))
            raise typer.Exit(1)

    def create_check(self, name: str, check_type: str, url: Optional[str] = None, host: Optional[str] = None, port: Optional[int] = None, interval: Optional[int] = None, timeout: int = 30, parameters: Optional[str] = None, pw_script_file: Optional[str] = None, from_file: Optional[str] = None, regions: Optional[str] = None, cron: Optional[str] = None):
        """Create a new monitoring check"""
        try:
            import json
            import os

            if interval is not None and cron is not None:
                self.display_error("Use either --interval or --cron, not both")
                raise typer.Exit(1)

            checks_api = self.get_client()

            # If creating from file, parse file and merge with command line options
            if from_file:
                file_data = self._parse_check_file(from_file)

                # Filter only SDK-recognized fields from file data
                # This ignores marketplace-specific fields and other extensions
                sdk_fields = ["name", "type", "url", "host", "port", "interval", "scheduling_type", "cron_schedule", "timeout", "parameters", "active", "secrets"]
                filtered_file_data = {k: v for k, v in file_data.items() if k in sdk_fields}

                # Command line options take precedence over file data
                check_data = {
                    "name": filtered_file_data.get("name", name),
                    "type": filtered_file_data.get("type", check_type),
                    "timeout": filtered_file_data.get("timeout", timeout)
                }

                # Scheduling from the file applies unless --interval or --cron was given explicitly
                if interval is None and cron is None:
                    if filtered_file_data.get("scheduling_type") == "cron" or (
                        filtered_file_data.get("cron_schedule") and "interval" not in filtered_file_data
                    ):
                        cron = filtered_file_data.get("cron_schedule")
                        if not cron:
                            self.display_error("cron_schedule is required in the file when scheduling_type is 'cron'")
                            raise typer.Exit(1)
                    else:
                        interval = filtered_file_data.get("interval")

                # Override with command line values if provided (but only if they were explicitly changed from defaults)
                if timeout != 30:  # Only override if timeout was explicitly provided
                    check_data["timeout"] = timeout

                # Handle URL from file
                if url is None and filtered_file_data.get("url"):
                    url = filtered_file_data["url"]
                elif url is not None:
                    # Command line URL takes precedence
                    pass

                # Handle host/port from file
                if host is None and filtered_file_data.get("host"):
                    host = filtered_file_data["host"]
                elif host is not None:
                    # Command line host takes precedence
                    pass

                if port is None and filtered_file_data.get("port"):
                    port = filtered_file_data["port"]
                elif port is not None:
                    # Command line port takes precedence
                    pass

                # Handle parameters from file
                file_parameters = filtered_file_data.get("parameters")
                if file_parameters and parameters is None:
                    # Use file parameters if no command line parameters
                    parameters = json.dumps(file_parameters) if isinstance(file_parameters, dict) else file_parameters

                # Handle secrets from file
                if filtered_file_data.get("secrets"):
                    check_data["secrets"] = filtered_file_data["secrets"]

                # Handle pw_script_file from file (this is CLI-specific, not sent to SDK)
                if pw_script_file is None and file_data.get("pw_script_file"):
                    pw_script_file = file_data["pw_script_file"]

                # Show info about ignored fields if any
                ignored_fields = [k for k in file_data.keys() if k not in sdk_fields and k != "pw_script_file"]
                if ignored_fields:
                    self.display_info(f"Ignoring non-SDK fields from file: {', '.join(ignored_fields)}")

                self.display_info(f"Creating check from file: {from_file}")
            else:
                # Build check data normally
                check_data = {
                    "name": name,
                    "type": check_type,
                    "timeout": timeout
                }

            if cron is not None:
                check_data["scheduling_type"] = "cron"
                check_data["cron_schedule"] = cron
            else:
                check_data["scheduling_type"] = "interval"
                check_data["interval"] = interval if interval is not None else 300

            # Add URL if provided (required for web, api, ssl checks)
            if url is not None:
                check_data["url"] = url

            # Add host/port for TCP/SSL checks
            if host is not None:
                check_data["host"] = host
            if port is not None:
                check_data["port"] = port

            # Handle pw_script_file option
            params_dict = {}
            if pw_script_file is not None:
                if not os.path.exists(pw_script_file):
                    self.display_error(f"Playwright script file not found: {pw_script_file}")
                    raise typer.Exit(1)

                try:
                    with open(pw_script_file, 'r', encoding='utf-8') as f:
                        pw_script_content = f.read().strip()

                    if not pw_script_content:
                        self.display_error(f"Playwright script file is empty: {pw_script_file}")
                        raise typer.Exit(1)

                    params_dict["pw_script"] = pw_script_content
                    self.display_info(f"Loaded Playwright script from: {pw_script_file}")

                except IOError as e:
                    self.display_error(f"Failed to read Playwright script file: {str(e)}")
                    raise typer.Exit(1)

            # Handle regions parameter - add to params_dict if provided and not in parameters
            if regions is not None and parameters is None:
                # Parse comma-separated regions into a list
                regions_list = [r.strip() for r in regions.split(',') if r.strip()]
                if regions_list:
                    params_dict["regions"] = regions_list

            # Parse parameters JSON if provided (this takes precedence over --regions)
            if parameters is not None:
                try:
                    parsed_params = json.loads(parameters)
                    # Merge with pw_script from file if both are provided
                    params_dict.update(parsed_params)
                except json.JSONDecodeError as e:
                    self.display_error(f"Invalid JSON in --parameters: {str(e)}")
                    self.display_info("Example: --parameters '{\"pw_script\": \"const { test } = require('@playwright/test'); test('example', async ({ page }) => { await page.goto('https://example.com'); });\", \"regions\": [\"US\", \"EU\"]}'")
                    raise typer.Exit(1)

            # Add parameters to check_data if we have any
            if params_dict:
                check_data["parameters"] = params_dict

            # Validation based on check type - use the actual type from check_data
            actual_check_type = check_data.get("type", check_type)
            if actual_check_type in ['web', 'api'] and not url:
                self.display_error(f"URL is required for {actual_check_type} checks")
                raise typer.Exit(1)

            if actual_check_type in ['tcp', 'icmp', 'dns'] and not host:
                self.display_error(f"Host is required for {actual_check_type} checks")
                raise typer.Exit(1)

            if actual_check_type in ['ssl'] and not (url or host):
                self.display_error(f"Either URL or host is required for {actual_check_type} checks")
                raise typer.Exit(1)

            if actual_check_type in ['synthetic', 'multistep'] and not params_dict.get('pw_script'):
                self.display_error(f"Playwright script is required for {actual_check_type} checks. Use --pw-script-file or --parameters with pw_script")
                raise typer.Exit(1)

            # Use the actual SDK method
            check = checks_api.v1_checks_post(monitor_check=check_data)

            # Build success message - use the actual name from check_data, not the parameter
            actual_name = check_data.get("name", name)
            actual_type = check_data.get("type", check_type)
            success_details = [f"ID: {check.id}", f"Type: {actual_type}"]
            if url:
                success_details.append(f"URL: {url}")
            if host:
                success_details.append(f"Host: {host}")
            if port:
                success_details.append(f"Port: {port}")
            if pw_script_file:
                success_details.append(f"Script: loaded from {pw_script_file}")
            success_details.append(f"Schedule: {_format_schedule(check)}")

            if self.output_format in ['json', 'yaml']:
                self.output_data(to_plain(check))
                return

            self.display_success(
                f"Check '{actual_name}' created successfully!\n" + "\n".join(success_details),
                "✅ Check Created"
            )

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to create check: {str(e)}")
            raise typer.Exit(1)

    def update_check(self, check_id: str, name: Optional[str] = None, url: Optional[str] = None, host: Optional[str] = None, port: Optional[int] = None, interval: Optional[int] = None, timeout: Optional[int] = None, active: Optional[bool] = None, parameters: Optional[str] = None, pw_script_file: Optional[str] = None, regions: Optional[str] = None, cron: Optional[str] = None):
        """Update an existing check"""
        try:
            import json
            import os
            checks_api = self.get_client()

            # Build update data
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if url is not None:
                update_data["url"] = url
            if host is not None:
                update_data["host"] = host
            if port is not None:
                update_data["port"] = port
            if interval is not None and cron is not None:
                self.display_error("Use either --interval or --cron, not both")
                raise typer.Exit(1)
            if interval is not None:
                update_data["scheduling_type"] = "interval"
                update_data["interval"] = interval
            if cron is not None:
                update_data["scheduling_type"] = "cron"
                update_data["cron_schedule"] = cron
            if timeout is not None:
                update_data["timeout"] = timeout
            if active is not None:
                update_data["active"] = active

            # Handle pw_script_file option
            params_dict = {}
            if pw_script_file is not None:
                if not os.path.exists(pw_script_file):
                    self.display_error(f"Playwright script file not found: {pw_script_file}")
                    raise typer.Exit(1)

                try:
                    with open(pw_script_file, 'r', encoding='utf-8') as f:
                        pw_script_content = f.read().strip()

                    if not pw_script_content:
                        self.display_error(f"Playwright script file is empty: {pw_script_file}")
                        raise typer.Exit(1)

                    params_dict["pw_script"] = pw_script_content
                    self.display_info(f"Loaded Playwright script from: {pw_script_file}")

                except IOError as e:
                    self.display_error(f"Failed to read Playwright script file: {str(e)}")
                    raise typer.Exit(1)

            # Handle regions parameter - add to params_dict if provided and not in parameters
            if regions is not None and parameters is None:
                # Parse comma-separated regions into a list
                regions_list = [r.strip() for r in regions.split(',') if r.strip()]
                if regions_list:
                    params_dict["regions"] = regions_list

            # Parse parameters JSON if provided (this takes precedence over --regions)
            if parameters is not None:
                try:
                    parsed_params = json.loads(parameters)
                    # Merge with pw_script from file if both are provided
                    params_dict.update(parsed_params)
                except json.JSONDecodeError as e:
                    self.display_error(f"Invalid JSON in --parameters: {str(e)}")
                    self.display_info("Example: --parameters '{\"pw_script\": \"const { test } = require('@playwright/test'); test('example', async ({ page }) => { await page.goto('https://example.com'); });\", \"regions\": [\"US\", \"EU\"]}'")
                    raise typer.Exit(1)

            # Add parameters to update_data if we have any
            if params_dict:
                update_data["parameters"] = params_dict

            if not update_data:
                self.display_warning("No updates specified. Use --name, --url, --host, --port, --interval, --cron, --timeout, --active/--inactive, --parameters, or --pw-script-file to update.")
                return

            # Use the actual SDK method with the correct parameter name
            check = checks_api.v1_checks_check_id_patch(check_id=check_id, monitor_check1=update_data)

            status_msg = ""
            if active is not None:
                status_msg = f"\nStatus: {'Active' if active else 'Paused'}"

            # Show what was updated
            updated_fields = []
            if name is not None:
                updated_fields.append(f"name: {check.name}")
            if url is not None:
                updated_fields.append(f"url: {check.url}")
            if host is not None:
                updated_fields.append(f"host: {check.host}")
            if port is not None:
                updated_fields.append(f"port: {check.port}")
            if interval is not None or cron is not None:
                updated_fields.append(f"schedule: {_format_schedule(check)}")
            if timeout is not None:
                updated_fields.append(f"timeout: {check.timeout}s")
            if pw_script_file is not None:
                updated_fields.append(f"pw_script: loaded from {pw_script_file}")
            if parameters is not None:
                updated_fields.append("parameters: updated")

            update_summary = "\n".join([f"• {field}" for field in updated_fields]) if updated_fields else ""

            if self.output_format in ['json', 'yaml']:
                self.output_data(to_plain(check))
                return

            self.display_success(
                f"Check {check_id} updated successfully!\n{update_summary}{status_msg}",
                "✅ Check Updated"
            )

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to update check: {str(e)}")
            raise typer.Exit(1)

    def delete_check(self, check_id: str, confirm: bool = False):
        """Delete a monitoring check"""
        try:
            if not confirm:
                if not Confirm.ask(f"Are you sure you want to delete check {check_id}?"):
                    self.console.print("[yellow]Operation cancelled.[/yellow]")
                    return

            client = self.get_client()
            client.v1_checks_check_id_delete(check_id=check_id)

            if self.machine_output:
                self.output_data({"deleted": True, "id": check_id})
                return

            self.display_success(
                f"Check {check_id} deleted successfully!",
                "✅ Check Deleted"
            )

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to delete check: {str(e)}")
            raise typer.Exit(1)

    def get_check_results(self, check_id: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None, page: int = 1, page_size: int = 20, status: Optional[str] = None, check_type: Optional[str] = None, region: Optional[str] = None, result_id: Optional[str] = None):
        """Get check results using unified results API"""
        try:
            unified_api = self.get_unified_results_client()

            # Build parameters for the unified API call
            params = {
                "page": page,
                "page_size": page_size
            }

            # Add check_id only if provided
            if check_id:
                params["check_id"] = check_id

            # Add result_id if provided (for fetching specific result)
            if result_id:
                params["result_id"] = result_id

            # Add optional filters
            if from_date:
                params["start_date"] = parse_time_arg(from_date, "--from")
            if to_date:
                params["end_date"] = parse_time_arg(to_date, "--to")
            if status:
                params["status"] = status
            if check_type:
                params["check_type"] = check_type
            if region:
                params["region"] = region

            # Use the unified results API
            response = unified_api.v1_checks_all_results_get(**params)

            if not hasattr(response, 'results') or not response.results:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({"results": [], "total": 0, "message": "No results found"})
                else:
                    self.display_info("No results found.")
                return

            # If result_id was specified, we're fetching a single result - display it with full formatting
            if result_id and len(response.results) == 1:
                result = response.results[0]

                if self.output_format in ['json', 'yaml']:
                    result_dict = {
                        "id": str(result.id) if hasattr(result, 'id') and result.id else None,
                        "check_id": result.check_id if hasattr(result, 'check_id') else None,
                        "check_name": result.check_name if hasattr(result, 'check_name') else None,
                        "check_type": result.check_type if hasattr(result, 'check_type') else None,
                        "status": result.status if hasattr(result, 'status') else None,
                        "created_at": result.created_at if hasattr(result, 'created_at') and result.created_at else None,
                        "response_time": result.response_time if hasattr(result, 'response_time') else None,
                        "error_message": result.error_message if hasattr(result, 'error_message') else None,
                        "check_server_id": result.check_server_id if hasattr(result, 'check_server_id') else None,
                        "region": result.region if hasattr(result, 'region') else None,
                        "result_type": result.result_type if hasattr(result, 'result_type') else None,
                        "check_metadata": result.check_metadata if hasattr(result, 'check_metadata') else None,
                        "check_server": {
                            "ip_address": result.check_server.ip_address if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'ip_address') else None,
                            "country": result.check_server.country if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'country') else None,
                            "region": result.check_server.region if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'region') else None
                        } if hasattr(result, 'check_server') and result.check_server else None
                    }
                    self.output_data(result_dict)
                else:
                    # Display with full formatting using _display_detailed_result
                    self._display_detailed_result(result, verbose=True)
                return

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                results_data = []
                for result in response.results:
                    result_dict = {
                        "id": str(result.id) if hasattr(result, 'id') and result.id else None,
                        "check_id": result.check_id if hasattr(result, 'check_id') else None,
                        "check_name": result.check_name if hasattr(result, 'check_name') else None,
                        "check_type": result.check_type if hasattr(result, 'check_type') else None,
                        "status": result.status if hasattr(result, 'status') else None,
                        "created_at": result.created_at if hasattr(result, 'created_at') and result.created_at else None,
                        "response_time": result.response_time if hasattr(result, 'response_time') else None,
                        "error_message": result.error_message if hasattr(result, 'error_message') else None,
                        "check_server_id": result.check_server_id if hasattr(result, 'check_server_id') else None,
                        "region": result.region if hasattr(result, 'region') else None,
                        "result_type": result.result_type if hasattr(result, 'result_type') else None,
                        "check_metadata": result.check_metadata if hasattr(result, 'check_metadata') else None,
                        "check_server": {
                            "ip_address": result.check_server.ip_address if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'ip_address') else None,
                            "country": result.check_server.country if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'country') else None,
                            "region": result.check_server.region if hasattr(result, 'check_server') and result.check_server and hasattr(result.check_server, 'region') else None
                        } if hasattr(result, 'check_server') and result.check_server else None
                    }
                    results_data.append(result_dict)

                pagination_info = {}
                if hasattr(response, 'pagination') and response.pagination:
                    pagination_info = {
                        "page": response.pagination.get('page', page),
                        "page_size": response.pagination.get('page_size', page_size),
                        "total_items": response.pagination.get('total_items', len(results_data)),
                        "total_pages": response.pagination.get('total_pages', 1)
                    }

                self.output_data({
                    "results": results_data,
                    "pagination": pagination_info if pagination_info else {"page": page, "page_size": page_size, "total_items": len(results_data)}
                })

            else:
                # Create table for human-readable output
                table_title = f"Check Results for {check_id}" if check_id else "All Check Results"
                table = Table(title=table_title)
                table.add_column("Result ID", style="dim", min_width=15)
                table.add_column("Check/Job ID", style="cyan", min_width=15)
                table.add_column("Timestamp", style="cyan")
                table.add_column("Check Name", style="green", max_width=20)
                table.add_column("Type", style="blue")
                table.add_column("Status", style="green")
                table.add_column("Response Time", style="yellow")
                table.add_column("Region", style="magenta", max_width=12)
                table.add_column("Error", style="red", max_width=25)

                for result in response.results:
                    # Extract result ID - never truncate IDs
                    result_id = str(result.id) if hasattr(result, 'id') and result.id else "-"

                    # Extract check_id or job_id based on result type - never truncate IDs
                    check_or_job_id = "-"
                    if hasattr(result, 'check_id') and result.check_id:
                        check_or_job_id = str(result.check_id)
                    elif hasattr(result, 'result_type') and result.result_type == 'on_demand':
                        # For on-demand results, we might not have check_id, show as on-demand
                        check_or_job_id = "[dim]on-demand[/dim]"

                    # Extract timestamp
                    timestamp = result.created_at.strftime("%m-%d %H:%M:%S") if hasattr(result, 'created_at') and result.created_at else "-"

                    # Check name
                    check_name = result.check_name if hasattr(result, 'check_name') and result.check_name else "-"
                    if len(check_name) > 19:
                        check_name = check_name[:19] + "…"

                    # Check type
                    check_type_display = result.check_type if hasattr(result, 'check_type') and result.check_type else "-"

                    # Determine status with emoji
                    status_emoji = "✅" if hasattr(result, 'status') and result.status == 'ok' else "❌"
                    status_color = "green" if hasattr(result, 'status') and result.status == 'ok' else "red"
                    status_display = f"[{status_color}]{status_emoji} {result.status}[/{status_color}]" if hasattr(result, 'status') and result.status else "-"

                    # Extract response time
                    response_time = f"{result.response_time}ms" if hasattr(result, 'response_time') and result.response_time is not None else "-"

                    # Extract region
                    region_display = result.region if hasattr(result, 'region') and result.region else "-"
                    if len(region_display) > 11:
                        region_display = region_display[:11] + "…"

                    # Extract error message
                    error_message = "-"
                    if hasattr(result, 'error_message') and result.error_message:
                        error_message = result.error_message
                        # Truncate long error messages
                        if len(error_message) > 24:
                            error_message = error_message[:24] + "…"

                    table.add_row(
                        result_id,
                        check_or_job_id,
                        timestamp,
                        check_name,
                        check_type_display,
                        status_display,
                        response_time,
                        region_display,
                        error_message
                    )

                self.console.print(table)

                # Show pagination info and hint about detailed view
                if hasattr(response, 'pagination') and response.pagination:
                    pagination = response.pagination
                    total_items = pagination.get('total_items', len(response.results))
                    total_pages = pagination.get('total_pages', 1)
                    current_page = pagination.get('page', page)
                    page_size_actual = pagination.get('page_size', page_size)

                    self.console.print(f"\n[dim]Showing {len(response.results)} results • Page {current_page} of {total_pages} • {total_items} total items • {page_size_actual} per page[/dim]")
                else:
                    self.console.print(f"\n[dim]Found {len(response.results)} results[/dim]")

                # Provide helpful hints based on context
                hints = []
                hints.append("Use 'pngr checks result <result-id>' for detailed result info")
                if not check_id:
                    hints.append("Use 'pngr checks list' to see all available checks and their IDs")
                    hints.append("Filter results: --type <type>, --status <status>, --region <region>")

                for hint in hints:
                    self.console.print(f"[dim]💡 {hint}[/dim]")

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to get check results: {str(e)}")
            raise typer.Exit(1)

    def get_check_result(self, result_id: str):
        """Get detailed information for a specific check result"""
        try:
            checks_api = self.get_client()

            # Parse the result ID to extract check_id and check_result_id
            # The result_id format might be "check_id:result_id" or just "result_id"
            # We need to determine the check_id somehow - for now, we'll ask user to provide it

            # Since we need both check_id and check_result_id, we'll need to modify the command
            # For now, let's show an error and guide the user
            self.display_error("This command needs both check ID and result ID.")
            self.display_info("Usage: pngr checks result <check-id> <result-id>")
            self.display_info("Or use: pngr checks results <check-id> to list all results first")
            return

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to get result details: {str(e)}")
            raise typer.Exit(1)

    def get_check_result_detailed(self, result_id: str, verbose: bool = False):
        """Get detailed information for a specific check result using result_id"""
        try:
            unified_api = self.get_unified_results_client()

            # Use the unified results API with result_id filter
            response = unified_api.v1_checks_all_results_get(result_id=result_id)

            if not hasattr(response, 'results') or not response.results or len(response.results) == 0:
                self.display_error(f"Result {result_id} not found")
                raise typer.Exit(1)

            result = response.results[0]

            if self.output_format in ['json', 'yaml']:
                # Full result data for JSON/YAML
                result_data = {
                    "id": str(result.id) if hasattr(result, 'id') else None,
                    "check_id": result.check_id if hasattr(result, 'check_id') else None,
                    "status": result.status if hasattr(result, 'status') else None,
                    "created_at": result.created_at if hasattr(result, 'created_at') and result.created_at else None,
                    "response_time": result.response_time if hasattr(result, 'response_time') else None,
                    "error_message": result.error_message if hasattr(result, 'error_message') else None,
                    "check_server_id": result.check_server_id if hasattr(result, 'check_server_id') else None,
                    "check_metadata": result.check_metadata if hasattr(result, 'check_metadata') else None
                }
                self.output_data(result_data)
            else:
                # Rich formatted detailed view
                self._display_detailed_result(result, verbose)

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to get result details: {str(e)}")
            raise typer.Exit(1)

    def _display_detailed_result(self, result, verbose: bool = False):
        """Display detailed result information in a rich format"""

        # Basic information
        # Handle response time display: 0 means <1ms, None/missing means N/A
        if hasattr(result, 'response_time') and result.response_time is not None:
            if result.response_time == 0:
                response_time_display = "<1ms"
            else:
                response_time_display = f"{result.response_time}ms"
        else:
            response_time_display = 'N/A'

        basic_info = f"""[bold cyan]Basic Information:[/bold cyan]
• Result ID: [white]{result.id}[/white]
• Check ID: [white]{result.check_id}[/white]
• Status: [{"green" if result.status == "ok" else "red"}]{result.status}[/{"green" if result.status == "ok" else "red"}]
• Timestamp: [white]{result.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if result.created_at else 'Unknown'}[/white]
• Response Time: [yellow]{response_time_display}[/yellow]
• Check Server: [magenta]{result.check_server_id if result.check_server_id else 'Unknown'}[/magenta]"""

        # Add check server details if available
        if hasattr(result, 'check_server') and result.check_server:
            server = result.check_server
            basic_info += f"""
• Server IP: [white]{server.ip_address if hasattr(server, 'ip_address') else 'Unknown'}[/white]
• Server Country: [white]{server.country if hasattr(server, 'country') else 'Unknown'}[/white]
• Server Region: [white]{server.region if hasattr(server, 'region') else 'Unknown'}[/white]"""

        # Error information
        error_info = ""
        if hasattr(result, 'error_message') and result.error_message:
            error_info = f"""
[bold red]Error Information:[/bold red]
• Error: [red]{result.error_message}[/red]"""

        # Metadata analysis - handle different check types
        metadata_info = ""
        if hasattr(result, 'check_metadata') and result.check_metadata:
            metadata = result.check_metadata

            if isinstance(metadata, dict):
                metadata_info = self._format_metadata_by_type(metadata, verbose)

        # Combine all sections
        full_info = basic_info
        if error_info:
            full_info += error_info
        if metadata_info:
            full_info += metadata_info

        panel = Panel(
            full_info,
            title=f"🔍 Result Details: {result.id}",
            border_style="blue",
            padding=(1, 2),
        )

        self.console.print(panel)

    def _format_metadata_by_type(self, metadata, verbose: bool = False):
        """Format metadata using the appropriate formatter"""
        from ..formatters.registry import FormatterRegistry
        registry = FormatterRegistry(verbose)
        return registry.format_metadata(metadata)

    def list_regions(self, check_type: Optional[str] = None):
        """List available regions for checks"""
        try:
            checks_api = self.get_client()

            # Get regions with optional check_type filter
            if check_type:
                response = checks_api.v1_checks_get_regions_get(check_type=check_type)
            else:
                response = checks_api.v1_checks_get_regions_get()

            if not hasattr(response, 'regions') or not response.regions:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({"regions": [], "total": 0, "message": "No regions found"})
                else:
                    self.display_info("No regions found.")
                return

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                regions_data = []
                for region in response.regions:
                    region_dict = {
                        "id": str(region.id) if hasattr(region, 'id') and region.id else None,
                        "display_name": region.display_name if hasattr(region, 'display_name') and region.display_name else None,
                        "aliases": region.aliases if hasattr(region, 'aliases') and region.aliases else None,
                        "available_check_types": region.available_check_types if hasattr(region, 'available_check_types') and region.available_check_types else None
                    }
                    regions_data.append(region_dict)

                self.output_data({
                    "regions": regions_data,
                    "total": len(regions_data),
                    "filter": {"check_type": check_type} if check_type else None
                })
            else:
                # Create table for default output
                table_title = f"Available Regions for {check_type.upper()} checks" if check_type else "Available Regions"
                table = Table(title=table_title)
                table.add_column("Region ID", style="cyan", min_width=15)
                table.add_column("Display Name", style="green", min_width=25)
                table.add_column("Aliases", style="yellow", min_width=20)
                table.add_column("Available Check Types", style="white")

                for region in response.regions:
                    # Extract region data using actual SDK attributes
                    region_id = str(region.id) if hasattr(region, 'id') and region.id else "-"
                    display_name = region.display_name if hasattr(region, 'display_name') and region.display_name else "-"

                    # Handle aliases
                    aliases_display = "-"
                    if hasattr(region, 'aliases') and region.aliases:
                        if isinstance(region.aliases, list):
                            aliases_display = ", ".join(region.aliases)
                        else:
                            aliases_display = str(region.aliases)

                    # Handle available check types
                    available_types = "-"
                    if hasattr(region, 'available_check_types') and region.available_check_types:
                        if isinstance(region.available_check_types, list):
                            available_types = ", ".join(region.available_check_types)
                        else:
                            available_types = str(region.available_check_types)

                    table.add_row(
                        region_id,
                        display_name,
                        aliases_display,
                        available_types
                    )

                self.console.print(table)

                # Show summary
                filter_text = f" for {check_type} checks" if check_type else ""
                self.console.print(f"\n[dim]Found {len(response.regions)} regions{filter_text}[/dim]")

                # Show helpful hints
                if not check_type:
                    self.console.print(f"[dim]💡 Filter by check type: pngr checks list-regions --type <type>[/dim]")
                    self.console.print(f"[dim]💡 Available check types: web, api, tcp, ssl, synthetic, multistep[/dim]")

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to list regions: {str(e)}")
            raise typer.Exit(1)

    def assign_check_to_group(self, check_id: str, group_id: Optional[str] = None):
        """Assign a check to a group or remove it from a group"""
        try:
            # Get the CheckGroupsApi client for group assignment
            api_key = get_api_key()
            if not api_key:
                self.display_error("API key not found. Use 'pngr auth login --api-key <key>' to set it.")
                raise typer.Exit(1)

            try:
                from pingera import ApiClient, Configuration
                from pingera.api import CheckGroupsApi
                from ..utils.config import get_config

                # Configure the client
                configuration = Configuration()
                configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
                configuration.api_key['apiKeyAuth'] = api_key

                # Create API client
                api_client = ApiClient(configuration)
                groups_api = CheckGroupsApi(api_client)
            except ImportError:
                self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
                raise typer.Exit(1)

            # Prepare assignment data
            if group_id == "null" or group_id == "none":
                assignment_data = {"group_id": None}
                action_msg = "removed from group"
            else:
                assignment_data = {"group_id": group_id}
                action_msg = f"assigned to group {group_id}"

            # Use the actual SDK method
            result = groups_api.v1_checks_check_id_group_patch(check_id=check_id, generated=assignment_data)

            if self.machine_output:
                self.output_model(result)
                return

            self.display_success(
                f"Check {check_id} {action_msg} successfully!",
                "✅ Group Assignment Updated"
            )

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to assign check to group: {str(e)}")
            raise typer.Exit(1)

# Create Typer app for checks commands
app = typer.Typer(name="checks", help="🔍 Manage monitoring checks", no_args_is_help=True)


@app.command("list")
def list_checks(
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Items per page"),
    check_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by check type (web, api, ssl, tcp, icmp, dns, synthetic, multistep)"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status. Multiple statuses can be separated by commas (e.g., 'ok,failed')"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name using case-insensitive partial matching (max 100 chars)"),
    group_id: Optional[str] = typer.Option(None, "--group-id", "-g", help="Filter by group ID"),
):
    """List monitoring checks with advanced filtering options"""
    from ..utils.config import get_output_format

    # Validate name length
    if name and len(name) > 100:
        typer.echo("Error: Name filter cannot exceed 100 characters", err=True)
        raise typer.Exit(1)

    # Validate check type
    if check_type and check_type not in SUPPORTED_CHECK_TYPES:
        typer.echo(f"Error: Invalid check type '{check_type}'. Must be one of: {', '.join(SUPPORTED_CHECK_TYPES)}", err=True)
        raise typer.Exit(1)

    # Validate status values if provided
    if status:
        valid_statuses = ["ok", "failed", "degraded", "timeout", "pending", "paused"]
        status_list = [s.strip() for s in status.split(",")]
        for s in status_list:
            if s not in valid_statuses:
                typer.echo(f"Error: Invalid status '{s}'. Must be one of: {', '.join(valid_statuses)}", err=True)
                raise typer.Exit(1)

    checks_cmd = ChecksCommand(get_output_format())
    checks_cmd.list_checks(page, page_size, check_type, status, name, group_id)


@app.command("get")
def get_check(
    check_id: str = typer.Argument(..., help="Check ID to retrieve"),
):
    """Get specific check details"""
    from ..utils.config import get_output_format
    checks_cmd = ChecksCommand(get_output_format())
    checks_cmd.get_check(check_id)


@app.command("create")
def create_check(
    name: str = typer.Option("", "--name", "-n", help="Check name (required if not using --from-file)"),
    check_type: str = typer.Option("web", "--type", "-t", help="Check type (web, api, tcp, ssl, icmp, dns, synthetic, multistep)"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL to monitor (required for web, api, ssl checks)"),
    host: Optional[str] = typer.Option(None, "--host", help="Hostname/IP for TCP/SSL/ICMP/DNS checks (max 255 characters)"),
    port: Optional[int] = typer.Option(None, "--port", help="Port number for TCP checks (1-65535)"),
    interval: Optional[int] = typer.Option(None, "--interval", "-i", help="Check interval in seconds (default: 300)"),
    cron: Optional[str] = typer.Option(None, "--cron", help="Cron expression to schedule the check instead of a fixed interval (e.g. '0 9 * * 1-5')"),
    timeout: int = typer.Option(30, "--timeout", help="Timeout in seconds"),
    parameters: Optional[str] = typer.Option(None, "--parameters", help="JSON string with check parameters (e.g., '{\"regions\": [\"US\", \"EU\"]}')"),
    pw_script_file: Optional[str] = typer.Option(None, "--pw-script-file", help="Path to file containing Playwright script for synthetic/multistep checks"),
    from_file: Optional[str] = typer.Option(None, "--from-file", "-f", help="Path to JSON or YAML file containing check configuration"),
    regions: Optional[str] = typer.Option(None, "--regions", help="Comma-separated list of regions (e.g., 'ru-central1,eu-west1')"),
):
    """Create a new monitoring check. Can be created from command line options or from a JSON/YAML file.

    When using --from-file:
    - Command line options override file values
    - File should contain check configuration in JSON or YAML format

    Parameters vary by check type:
    - web/api: --url required
    - tcp: --host required, --port optional
    - ssl: --url or --host required
    - icmp: --host required (hostname or IP to ping)
    - dns: --host required (domain name to query)
    - synthetic/multistep: --pw-script-file or --parameters with pw_script required"""
    from ..utils.config import get_output_format

    # Validate that we have either from_file or required parameters
    if not from_file and not name:
        typer.echo("Error: --name is required when not using --from-file", err=True)
        raise typer.Exit(1)

    # Validate check type
    if check_type not in SUPPORTED_CHECK_TYPES:
        typer.echo(f"Error: Invalid check type '{check_type}'. Must be one of: {', '.join(SUPPORTED_CHECK_TYPES)}", err=True)
        raise typer.Exit(1)

    checks_cmd = ChecksCommand(get_output_format())
    checks_cmd.create_check(name, check_type, url, host, port, interval, timeout, parameters, pw_script_file, from_file, regions, cron)


@app.command("update")
def update_check(
    check_id: str = typer.Argument(..., help="Check ID to update"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New check name"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="New URL"),
    host: Optional[str] = typer.Option(None, "--host", help="New hostname/IP for TCP/SSL checks (max 255 characters)"),
    port: Optional[int] = typer.Option(None, "--port", help="New port number for TCP checks (1-65535)"),
    interval: Optional[int] = typer.Option(None, "--interval", "-i", help="New interval in seconds (switches the check to interval scheduling)"),
    cron: Optional[str] = typer.Option(None, "--cron", help="Cron expression (switches the check to cron scheduling, e.g. '*/15 * * * *')"),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="New timeout in seconds"),
    active: bool = typer.Option(None, "--active/--inactive", help="Enable or disable the check"),
    parameters: Optional[str] = typer.Option(None, "--parameters", help="JSON string with check parameters (e.g., '{\"pw_script\": \"...\", \"regions\": [\"US\", \"EU\"]}')"),
    pw_script_file: Optional[str] = typer.Option(None, "--pw-script-file", help="Path to file containing Playwright script for synthetic/multistep checks"),
    regions: Optional[str] = typer.Option(None, "--regions", help="Comma-separated list of regions (e.g., 'ru-central1,eu-west1')"),
):
    """Update an existing check. Use --parameters to provide complex parameters like Playwright scripts, regions, etc."""
    from ..utils.config import get_output_format
    checks_cmd = ChecksCommand(get_output_format())
    checks_cmd.update_check(check_id, name, url, host, port, interval, timeout, active, parameters, pw_script_file, regions, cron)


@app.command("delete")
def delete_check(
    check_id: str = typer.Argument(..., help="Check ID to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
):
    """Delete a monitoring check"""
    from ..utils.config import get_output_format
    checks_cmd = ChecksCommand(get_output_format())
    checks_cmd.delete_check(check_id, confirm)


@app.command("results")
def get_results(
    check_id: Optional[str] = typer.Argument(None, help="Check ID (optional - if not provided, returns all results)"),
    from_date: Optional[str] = typer.Option(None, "--from", help="Start (ISO 8601 or relative like 7d, 24h) - max 6 months ago"),
    to_date: Optional[str] = typer.Option(None, "--to", help="End (ISO 8601 or relative)"),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Items per page (1-100)"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status (ok, failed, degraded, timeout, pending)"),
    check_type: Optional[str] = typer.Option(None, "--type", help="Filter by check type (web, api, tcp, ssl, synthetic, multistep)"),
    region: Optional[str] = typer.Option(None, "--region", help="Filter by region"),
    result_id: Optional[str] = typer.Option(None, "--result-id", "-r", help="Filter by specific result ID"),
):
    """Get check results with advanced filtering. If no check_id is provided, returns unified results across all checks. Use --result-id to fetch a specific result."""
    from ..utils.config import get_output_format

    # Validate check type
    if check_type and check_type not in SUPPORTED_CHECK_TYPES:
        typer.echo(f"Error: Invalid check type '{check_type}'. Must be one of: {', '.join(SUPPORTED_CHECK_TYPES)}", err=True)
        raise typer.Exit(1)

    checks_cmd = ChecksCommand(get_output_format())
    checks_cmd.get_check_results(check_id, from_date, to_date, page, page_size, status, check_type, region, result_id)


@app.command("result")
def get_result(
    result_id: str = typer.Argument(..., help="Result ID to retrieve detailed information for"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full detailed information including network requests"),
):
    """Get detailed information for a specific check result"""
    from ..utils.config import get_output_format
    checks_cmd = ChecksCommand(get_output_format())
    checks_cmd.get_check_result_detailed(result_id, verbose)


@app.command("list-regions")
def list_regions(
    check_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter regions by check type (web, api, tcp, ssl, synthetic, multistep)"),
):
    """List available regions for monitoring checks"""
    from ..utils.config import get_output_format

    # Validate check type
    if check_type and check_type not in SUPPORTED_CHECK_TYPES:
        typer.echo(f"Error: Invalid check type '{check_type}'. Must be one of: {', '.join(SUPPORTED_CHECK_TYPES)}", err=True)
        raise typer.Exit(1)

    checks_cmd = ChecksCommand(get_output_format())
    checks_cmd.list_regions(check_type)


@app.command("assign-group")
def assign_check_to_group(
    check_id: str = typer.Argument(..., help="Check ID to assign"),
    group_id: Optional[str] = typer.Option(None, "--group-id", "-g", help="Group ID to assign check to (use 'null' to remove from group)"),
):
    """Assign a check to a group or remove it from a group"""
    from ..utils.config import get_output_format
    checks_cmd = ChecksCommand(get_output_format())
    checks_cmd.assign_check_to_group(check_id, group_id)


# Import on-demand checks functionality from separate module
from .on_demand_checks import run_app, jobs_app

# Import check groups functionality
from .check_groups import app as groups_app

# Import check secrets functionality
from .check_secrets import app as check_secrets_app

# Import execution groups functionality
from .execution_groups import app as execution_groups_app

# Add the run, jobs, groups, secrets, and execution-groups subcommands to the main checks app
app.add_typer(run_app, name="run")
app.add_typer(jobs_app, name="jobs")
app.add_typer(groups_app, name="groups")
app.add_typer(check_secrets_app, name="secrets")
app.add_typer(execution_groups_app, name="execution-groups")

from .check_metrics import register as _register_metrics_commands  # noqa: E402

_register_metrics_commands(app)