
"""
Components commands for PingeraCLI
"""

from typing import Optional
from datetime import datetime

import typer
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from .base import BaseCommand
from ..utils.config import get_api_key


class ComponentsCommand(BaseCommand):
    """
    Commands for managing status page components
    """

    def __init__(self, output_format: Optional[str] = None, verbose: bool = False):
        super().__init__(output_format)
        self.verbose = verbose

    def get_client(self):
        """Get Pingera SDK client with authentication"""
        api_key = get_api_key()
        if not api_key:
            self.display_error("API key not found. Use 'pngr auth login --api-key <key>' to set it.")
            raise typer.Exit(1)

        try:
            from pingera import ApiClient, Configuration
            from pingera.api import StatusPagesComponentsApi
            from ..utils.config import get_config

            # Configure the client
            configuration = Configuration()
            configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return StatusPagesComponentsApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def list_components(self, page_id: str):
        """List components for a status page"""
        try:
            components_api = self.get_client()
            response = components_api.v1_pages_page_id_components_get(page_id=page_id)

            if not response:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({"components": [], "total": 0, "message": "No components found"})
                else:
                    self.display_info("No components found.")
                return

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                components_data = []
                for component in response:
                    component_dict = {
                        "id": str(component.id) if hasattr(component, 'id') and component.id else None,
                        "name": component.name if hasattr(component, 'name') and component.name else None,
                        "description": component.description if hasattr(component, 'description') and component.description else None,
                        "status": component.status if hasattr(component, 'status') and component.status else None,
                        "group_id": component.group_id if hasattr(component, 'group_id') and component.group_id else None,
                        "position": component.position if hasattr(component, 'position') else None,
                        "showcase": component.showcase if hasattr(component, 'showcase') else None,
                        "created_at": component.created_at.isoformat() if hasattr(component, 'created_at') and component.created_at else None,
                    }
                    components_data.append(component_dict)

                self.output_data({
                    "components": components_data,
                    "total": len(components_data),
                    "page_id": page_id
                })
            else:
                # Create table for default output
                table = Table(title=f"Components for Page {page_id}")
                table.add_column("ID", style="cyan", min_width=15)
                table.add_column("Name", style="green", min_width=20)
                table.add_column("Status", style="yellow", min_width=12)
                table.add_column("Group", style="blue")
                table.add_column("Position", style="magenta")
                table.add_column("Showcase", style="dim")

                for component in response:
                    component_id = str(component.id) if hasattr(component, 'id') and component.id else "-"
                    name = str(component.name) if hasattr(component, 'name') and component.name else "-"
                    status = str(component.status) if hasattr(component, 'status') and component.status else "-"
                    group_id = str(component.group_id) if hasattr(component, 'group_id') and component.group_id else "-"
                    position = str(component.position) if hasattr(component, 'position') else "-"
                    showcase = "✓" if hasattr(component, 'showcase') and component.showcase else ""

                    table.add_row(
                        component_id,
                        name,
                        status,
                        group_id,
                        position,
                        showcase
                    )

                self.console.print(table)
                self.console.print(f"\n[dim]Found {len(response)} components[/dim]")

        except Exception as e:
            self.display_error(f"Failed to list components: {str(e)}")
            raise typer.Exit(1)

    def get_component(self, page_id: str, component_id: str):
        """Get specific component details"""
        try:
            components_api = self.get_client()
            component = components_api.v1_pages_page_id_components_component_id_get(
                page_id=page_id,
                component_id=component_id
            )

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                component_data = {
                    "id": str(component.id) if hasattr(component, 'id') and component.id else None,
                    "name": component.name if hasattr(component, 'name') and component.name else None,
                    "description": component.description if hasattr(component, 'description') and component.description else None,
                    "status": component.status if hasattr(component, 'status') and component.status else None,
                    "group_id": component.group_id if hasattr(component, 'group_id') and component.group_id else None,
                    "position": component.position if hasattr(component, 'position') else None,
                    "showcase": component.showcase if hasattr(component, 'showcase') else None,
                    "only_show_if_degraded": component.only_show_if_degraded if hasattr(component, 'only_show_if_degraded') else None,
                    "start_date": component.start_date.isoformat() if hasattr(component, 'start_date') and component.start_date else None,
                    "created_at": component.created_at.isoformat() if hasattr(component, 'created_at') and component.created_at else None,
                    "updated_at": component.updated_at.isoformat() if hasattr(component, 'updated_at') and component.updated_at else None,
                }
                self.output_data(component_data)
            else:
                # Rich formatted output
                basic_info = f"""[bold cyan]Basic Information:[/bold cyan]
• ID: [white]{component.id}[/white]
• Name: [white]{component.name}[/white]
• Status: [white]{component.status if hasattr(component, 'status') and component.status else 'Not set'}[/white]
• Description: [white]{component.description if hasattr(component, 'description') and component.description else 'Not set'}[/white]"""

                settings_info = f"""
[bold cyan]Settings:[/bold cyan]
• Position: [white]{component.position if hasattr(component, 'position') else 'Not set'}[/white]
• Group ID: [white]{component.group_id if hasattr(component, 'group_id') and component.group_id else 'None'}[/white]
• Showcase: [white]{'Yes' if hasattr(component, 'showcase') and component.showcase else 'No'}[/white]
• Only show if degraded: [white]{'Yes' if hasattr(component, 'only_show_if_degraded') and component.only_show_if_degraded else 'No'}[/white]
• Start date: [white]{component.start_date.strftime('%Y-%m-%d') if hasattr(component, 'start_date') and component.start_date else 'Not set'}[/white]"""

                timestamps = f"""
[bold cyan]Timestamps:[/bold cyan]
• Created: [white]{component.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(component, 'created_at') and component.created_at else 'Unknown'}[/white]
• Updated: [white]{component.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(component, 'updated_at') and component.updated_at else 'Unknown'}[/white]"""

                full_info = f"{basic_info}{settings_info}{timestamps}"

                panel = Panel(
                    full_info,
                    title=f"🔧 Component: {component.name}",
                    border_style="blue",
                    padding=(1, 2),
                )

                self.console.print(panel)

        except Exception as e:
            self.display_error(f"Failed to get component: {str(e)}")
            raise typer.Exit(1)

    def create_component(
        self,
        page_id: str,
        name: str,
        description: Optional[str] = None,
        status: Optional[str] = None,
        group_id: Optional[str] = None,
        position: Optional[int] = None,
        showcase: bool = False,
        only_show_if_degraded: bool = False,
        start_date: Optional[str] = None,
    ):
        """Create a new component"""
        try:
            components_api = self.get_client()

            # Build component data
            component_data = {
                "name": name,
                "showcase": showcase,
                "only_show_if_degraded": only_show_if_degraded,
            }

            # Add optional fields
            if description:
                component_data["description"] = description
            if status:
                component_data["status"] = status
            if group_id:
                component_data["group_id"] = group_id
            if position is not None:
                component_data["position"] = position
            if start_date:
                component_data["start_date"] = start_date

            # Create the component
            component = components_api.v1_pages_page_id_components_post(
                page_id=page_id,
                component=component_data
            )

            # Build success message
            success_details = [
                f"ID: {component.id}",
                f"Name: {name}",
                f"Status: {status or 'operational'}"
            ]

            self.display_success(
                f"Component '{name}' created successfully!\n" + "\n".join(success_details),
                "✅ Component Created"
            )

        except Exception as e:
            self.display_error(f"Failed to create component: {str(e)}")
            raise typer.Exit(1)

    def update_component(
        self,
        page_id: str,
        component_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        group_id: Optional[str] = None,
        position: Optional[int] = None,
        showcase: Optional[bool] = None,
        only_show_if_degraded: Optional[bool] = None,
    ):
        """Update an existing component"""
        try:
            components_api = self.get_client()

            # Build component data with only provided fields
            component_data = {}

            if name is not None:
                component_data["name"] = name
            if description is not None:
                component_data["description"] = description
            if status is not None:
                component_data["status"] = status
            if group_id is not None:
                component_data["group_id"] = group_id
            if position is not None:
                component_data["position"] = position
            if showcase is not None:
                component_data["showcase"] = showcase
            if only_show_if_degraded is not None:
                component_data["only_show_if_degraded"] = only_show_if_degraded

            if not component_data:
                self.display_error("No fields provided to update")
                raise typer.Exit(1)

            # Update the component
            component = components_api.v1_pages_page_id_components_component_id_patch(
                page_id=page_id,
                component_id=component_id,
                component1=component_data
            )

            self.display_success(
                f"Component '{component_id}' updated successfully!",
                "✅ Component Updated"
            )

        except Exception as e:
            self.display_error(f"Failed to update component: {str(e)}")
            raise typer.Exit(1)

    def delete_component(self, page_id: str, component_id: str, confirm: bool = False):
        """Delete a component"""
        try:
            if not confirm:
                if not Confirm.ask(f"Are you sure you want to delete component {component_id}? This action cannot be undone."):
                    self.console.print("[yellow]Operation cancelled.[/yellow]")
                    return

            components_api = self.get_client()
            components_api.v1_pages_page_id_components_component_id_delete(
                page_id=page_id,
                component_id=component_id
            )

            self.display_success(
                f"Component {component_id} deleted successfully!",
                "✅ Component Deleted"
            )

        except Exception as e:
            self.display_error(f"Failed to delete component: {str(e)}")
            raise typer.Exit(1)

    def get_component_uptime(self, page_id: str, component_id: str, start: Optional[str] = None, end: Optional[str] = None):
        """Get uptime data for a specific component"""
        try:
            components_api = self.get_client()
            
            # Build parameters
            params = {}
            if start:
                params['start'] = start
            if end:
                params['end'] = end
            
            # Make API call
            uptime_data = components_api.v1_pages_page_id_components_component_id_uptime_get(
                page_id=page_id,
                component_id=component_id,
                **params
            )

            print(f"##### {uptime_data}")

            # Check if we got valid data
            if uptime_data is None:
                self.display_error("No uptime data returned from API")
                raise typer.Exit(1)

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                uptime_dict = {
                    "component_id": component_id,
                    "page_id": page_id,
                    "name": uptime_data.name if hasattr(uptime_data, 'name') and uptime_data.name else None,
                    "uptime_percentage": uptime_data.uptime_percentage if hasattr(uptime_data, 'uptime_percentage') and uptime_data.uptime_percentage is not None else None,
                    "range_start": uptime_data.range_start if hasattr(uptime_data, 'range_start') and uptime_data.range_start else start,
                    "range_end": uptime_data.range_end if hasattr(uptime_data, 'range_end') and uptime_data.range_end else end,
                    "major_outage": uptime_data.major_outage if hasattr(uptime_data, 'major_outage') and uptime_data.major_outage is not None else 0,
                    "partial_outage": uptime_data.partial_outage if hasattr(uptime_data, 'partial_outage') and uptime_data.partial_outage is not None else 0,
                    "related_events": uptime_data.related_events.id if hasattr(uptime_data, 'related_events') and hasattr(uptime_data.related_events, 'id') else [],
                    "warnings": uptime_data.warnings if hasattr(uptime_data, 'warnings') and uptime_data.warnings else [],
                }
                self.output_data(uptime_dict)
            else:
                # Rich formatted output
                uptime_pct = uptime_data.uptime_percentage if hasattr(uptime_data, 'uptime_percentage') and uptime_data.uptime_percentage is not None else 0
                
                # Color code based on uptime percentage
                if uptime_pct >= 99.9:
                    uptime_color = "green"
                elif uptime_pct >= 99.0:
                    uptime_color = "yellow"
                else:
                    uptime_color = "red"
                
                # Component name
                component_name = uptime_data.name if hasattr(uptime_data, 'name') and uptime_data.name else "Unknown"
                
                uptime_info = f"""[bold cyan]Component:[/bold cyan]
• Name: [white]{component_name}[/white]
• ID: [white]{component_id}[/white]

[bold cyan]Uptime Statistics:[/bold cyan]
• Uptime: [{uptime_color}]{uptime_pct:.3f}%[/{uptime_color}]"""

                # Date range
                range_start = uptime_data.range_start if hasattr(uptime_data, 'range_start') and uptime_data.range_start else start
                range_end = uptime_data.range_end if hasattr(uptime_data, 'range_end') and uptime_data.range_end else end
                
                if range_start or range_end:
                    uptime_info += f"""
• Period: [white]{range_start or 'Not specified'}[/white] to [white]{range_end or 'Not specified'}[/white]"""

                # Outage counts
                major_outage = uptime_data.major_outage if hasattr(uptime_data, 'major_outage') and uptime_data.major_outage is not None else 0
                partial_outage = uptime_data.partial_outage if hasattr(uptime_data, 'partial_outage') and uptime_data.partial_outage is not None else 0
                
                major_color = "red" if major_outage > 0 else "green"
                partial_color = "yellow" if partial_outage > 0 else "green"
                
                uptime_info += f"""
• Major Outages: [{major_color}]{major_outage}[/{major_color}]
• Partial Outages: [{partial_color}]{partial_outage}[/{partial_color}]"""

                # Related events
                if hasattr(uptime_data, 'related_events') and uptime_data.related_events and hasattr(uptime_data.related_events, 'id') and uptime_data.related_events.id:
                    event_ids = uptime_data.related_events.id
                    uptime_info += f"""

[bold cyan]Related Events:[/bold cyan]
• Event Count: [white]{len(event_ids)}[/white]"""
                    if self.verbose:
                        for event_id in event_ids[:10]:  # Show first 10 in verbose mode
                            uptime_info += f"\n  • [dim]{event_id}[/dim]"
                        if len(event_ids) > 10:
                            uptime_info += f"\n  • [dim]... and {len(event_ids) - 10} more[/dim]"
                    else:
                        uptime_info += "\n[dim]  Use --verbose to see event IDs[/dim]"

                # Warnings
                if hasattr(uptime_data, 'warnings') and uptime_data.warnings:
                    uptime_info += f"""

[bold yellow]Warnings:[/bold yellow]"""
                    for warning in uptime_data.warnings:
                        uptime_info += f"\n• [yellow]{warning}[/yellow]"

                panel = Panel(
                    uptime_info,
                    title=f"📊 Component Uptime: {component_name}",
                    border_style="blue",
                    padding=(1, 2),
                )

                self.console.print(panel)

        except Exception as e:
            self.display_error(f"Failed to get component uptime: {str(e)}")
            raise typer.Exit(1)

    # Create Typer app for components commands
app = typer.Typer(name="components", help="🔧 Manage status page components", no_args_is_help=True)


@app.command("list")
def list_components(
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
):
    """List components for a status page"""
    from ..utils.config import get_output_format
    components_cmd = ComponentsCommand(get_output_format())
    components_cmd.list_components(page_id)


@app.command("get")
def get_component(
    component_id: str = typer.Argument(..., help="Component ID to retrieve"),
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
):
    """Get specific component details"""
    from ..utils.config import get_output_format
    components_cmd = ComponentsCommand(get_output_format())
    components_cmd.get_component(page_id, component_id)


@app.command("create")
def create_component(
    name: str = typer.Option(..., "--name", "-n", help="Component name"),
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Component description"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Component status (operational, degraded_performance, partial_outage, major_outage)"),
    group_id: Optional[str] = typer.Option(None, "--group-id", "-g", help="Component group ID"),
    position: Optional[int] = typer.Option(None, "--position", help="Display position"),
    showcase: bool = typer.Option(False, "--showcase", help="Prominently display on status page"),
    only_show_if_degraded: bool = typer.Option(False, "--only-if-degraded", help="Only show when not operational"),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Monitoring start date (YYYY-MM-DD)"),
):
    """Create a new component"""
    from ..utils.config import get_output_format
    components_cmd = ComponentsCommand(get_output_format())
    components_cmd.create_component(
        page_id=page_id,
        name=name,
        description=description,
        status=status,
        group_id=group_id,
        position=position,
        showcase=showcase,
        only_show_if_degraded=only_show_if_degraded,
        start_date=start_date,
    )


@app.command("update")
def update_component(
    component_id: str = typer.Argument(..., help="Component ID to update"),
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Component name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Component description"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Component status"),
    group_id: Optional[str] = typer.Option(None, "--group-id", "-g", help="Component group ID"),
    position: Optional[int] = typer.Option(None, "--position", help="Display position"),
    showcase: Optional[bool] = typer.Option(None, "--showcase/--no-showcase", help="Prominently display on status page"),
    only_show_if_degraded: Optional[bool] = typer.Option(None, "--only-if-degraded/--always-show", help="Only show when not operational"),
):
    """Update an existing component"""
    from ..utils.config import get_output_format
    components_cmd = ComponentsCommand(get_output_format())
    components_cmd.update_component(
        page_id=page_id,
        component_id=component_id,
        name=name,
        description=description,
        status=status,
        group_id=group_id,
        position=position,
        showcase=showcase,
        only_show_if_degraded=only_show_if_degraded,
    )


@app.command("delete")
def delete_component(
    component_id: str = typer.Argument(..., help="Component ID to delete"),
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
):
    """Delete a component"""
    from ..utils.config import get_output_format
    components_cmd = ComponentsCommand(get_output_format())
    components_cmd.delete_component(page_id, component_id, confirm)


@app.command("uptime")
def get_component_uptime(
    component_id: str = typer.Argument(..., help="Component ID to get uptime for"),
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    start: Optional[str] = typer.Option(None, "--start", help="Start date (YYYY-MM-DD or ISO 8601)"),
    end: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD or ISO 8601)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information including event IDs"),
):
    """Get uptime data for a specific component"""
    from ..utils.config import get_output_format
    components_cmd = ComponentsCommand(get_output_format(), verbose=verbose)
    components_cmd.get_component_uptime(page_id, component_id, start, end)
