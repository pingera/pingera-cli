
"""
Incidents commands for PingeraCLI
"""

from typing import Optional
from datetime import datetime

import typer
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from .base import BaseCommand
from ..utils.config import get_api_key


class IncidentsCommand(BaseCommand):
    """
    Commands for managing status page incidents
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
            from pingera.api import StatusPagesIncidentsApi
            from ..utils.config import get_config

            # Configure the client
            configuration = Configuration()
            configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return StatusPagesIncidentsApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def list_incidents(
        self,
        page_id: str,
        component_id: Optional[str] = None,
        unresolved: bool = False,
        maintenance: bool = False,
    ):
        """List incidents for a status page with optional filters"""
        try:
            incidents_api = self.get_client()
            
            # Build parameters
            params = {}
            if component_id:
                params['component_id'] = component_id
            
            response = incidents_api.v1_pages_page_id_incidents_get(page_id=page_id, **params)
            
            # Apply client-side filters
            if response and (unresolved or maintenance):
                filtered_incidents = []
                for incident in response:
                    if unresolved:
                        # Filter for unresolved incidents (not resolved)
                        if hasattr(incident, 'status') and incident.status and incident.status != 'resolved':
                            filtered_incidents.append(incident)
                    elif maintenance:
                        # Filter for scheduled maintenance
                        if hasattr(incident, 'scheduled_for') and incident.scheduled_for:
                            filtered_incidents.append(incident)
                response = filtered_incidents

            if not response:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({"incidents": [], "total": 0, "message": "No incidents found"})
                else:
                    self.display_info("No incidents found.")
                return

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                incidents_data = []
                for incident in response:
                    incident_dict = {
                        "id": str(incident.id) if hasattr(incident, 'id') and incident.id else None,
                        "name": incident.name if hasattr(incident, 'name') and incident.name else None,
                        "status": incident.status if hasattr(incident, 'status') and incident.status else None,
                        "impact": incident.impact if hasattr(incident, 'impact') and incident.impact else None,
                        "created_at": incident.created_at.isoformat() if hasattr(incident, 'created_at') and incident.created_at else None,
                        "updated_at": incident.updated_at.isoformat() if hasattr(incident, 'updated_at') and incident.updated_at else None,
                        "resolved_at": incident.resolved_at if hasattr(incident, 'resolved_at') and incident.resolved_at else None,
                    }
                    incidents_data.append(incident_dict)

                self.output_data({
                    "incidents": incidents_data,
                    "total": len(incidents_data),
                    "page_id": page_id
                })
            else:
                # Create table for default output
                table = Table(title=f"Incidents for Page {page_id}")
                table.add_column("ID", style="cyan", min_width=15)
                table.add_column("Name", style="green", min_width=25)
                table.add_column("Status", style="yellow", min_width=15)
                table.add_column("Impact", style="red", min_width=12)
                table.add_column("Created", style="dim")

                for incident in response:
                    incident_id = str(incident.id) if hasattr(incident, 'id') and incident.id else "-"
                    name = str(incident.name) if hasattr(incident, 'name') and incident.name else "-"
                    status = str(incident.status) if hasattr(incident, 'status') and incident.status else "-"
                    impact = str(incident.impact) if hasattr(incident, 'impact') and incident.impact else "-"
                    
                    created_display = "-"
                    if hasattr(incident, 'created_at') and incident.created_at:
                        try:
                            created_display = incident.created_at.strftime("%Y-%m-%d %H:%M")
                        except (AttributeError, TypeError):
                            created_display = str(incident.created_at)

                    table.add_row(incident_id, name, status, impact, created_display)

                self.console.print(table)
                self.console.print(f"\n[dim]Found {len(response)} incidents[/dim]")

        except Exception as e:
            self.display_error(f"Failed to list incidents: {str(e)}")
            raise typer.Exit(1)

    def get_incident(self, page_id: str, incident_id: str):
        """Get specific incident details"""
        try:
            incidents_api = self.get_client()
            incident = incidents_api.v1_pages_page_id_incidents_incident_id_get(
                page_id=page_id,
                incident_id=incident_id
            )

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                # Parse incident_updates
                incident_updates_data = []
                if hasattr(incident, 'incident_updates') and incident.incident_updates:
                    for update in incident.incident_updates:
                        if isinstance(update, dict):
                            incident_updates_data.append(update)
                        else:
                            update_dict = {
                                "id": getattr(update, 'id', None),
                                "body": getattr(update, 'body', None),
                                "status": getattr(update, 'status', None),
                                "created_at": getattr(update, 'created_at', None),
                                "components": getattr(update, 'components', None),
                                "deliver_notifications": getattr(update, 'deliver_notifications', None),
                            }
                            incident_updates_data.append(update_dict)

                # Parse components
                components_data = []
                if hasattr(incident, 'components') and incident.components:
                    for comp in incident.components:
                        if isinstance(comp, dict):
                            components_data.append(comp)
                        else:
                            comp_dict = {
                                "id": getattr(comp, 'id', None),
                                "name": getattr(comp, 'name', None),
                                "status": getattr(comp, 'status', None),
                                "description": getattr(comp, 'description', None),
                            }
                            components_data.append(comp_dict)

                incident_data = {
                    "id": str(incident.id) if hasattr(incident, 'id') and incident.id else None,
                    "name": incident.name if hasattr(incident, 'name') and incident.name else None,
                    "status": incident.status if hasattr(incident, 'status') and incident.status else None,
                    "impact": incident.impact if hasattr(incident, 'impact') and incident.impact else None,
                    "body": incident.body if hasattr(incident, 'body') and incident.body else None,
                    "page_id": incident.page_id if hasattr(incident, 'page_id') and incident.page_id else None,
                    "created_at": incident.created_at.isoformat() if hasattr(incident, 'created_at') and incident.created_at else None,
                    "updated_at": incident.updated_at.isoformat() if hasattr(incident, 'updated_at') and incident.updated_at else None,
                    "resolved_at": incident.resolved_at if hasattr(incident, 'resolved_at') and incident.resolved_at else None,
                    "monitoring_at": incident.monitoring_at.isoformat() if hasattr(incident, 'monitoring_at') and incident.monitoring_at else None,
                    "incident_updates": incident_updates_data,
                    "components": components_data,
                    "postmortem_body": incident.postmortem_body if hasattr(incident, 'postmortem_body') and incident.postmortem_body else None,
                    "postmortem_published_at": incident.postmortem_published_at if hasattr(incident, 'postmortem_published_at') and incident.postmortem_published_at else None,
                }
                self.output_data(incident_data)
            else:
                # Rich formatted output
                basic_info = f"""[bold cyan]Basic Information:[/bold cyan]
• ID: [white]{incident.id}[/white]
• Name: [white]{incident.name}[/white]
• Status: [white]{incident.status if hasattr(incident, 'status') and incident.status else 'Not set'}[/white]
• Impact: [white]{incident.impact if hasattr(incident, 'impact') and incident.impact else 'Not set'}[/white]
• Page ID: [white]{incident.page_id if hasattr(incident, 'page_id') and incident.page_id else 'Unknown'}[/white]"""

                # Affected Components
                components_info = ""
                if hasattr(incident, 'components') and incident.components:
                    components_info = f"""

[bold cyan]Affected Components ({len(incident.components)}):[/bold cyan]"""
                    for comp in incident.components:
                        if isinstance(comp, dict):
                            comp_name = comp.get('name', 'Unknown')
                            comp_status = comp.get('status', 'unknown')
                            comp_id = comp.get('id', '')
                        else:
                            comp_name = getattr(comp, 'name', 'Unknown')
                            comp_status = getattr(comp, 'status', 'unknown')
                            comp_id = getattr(comp, 'id', '')
                        
                        status_color = {
                            'operational': 'green',
                            'degraded_performance': 'yellow',
                            'partial_outage': 'yellow',
                            'major_outage': 'red',
                            'under_maintenance': 'blue'
                        }.get(comp_status, 'white')
                        
                        if self.verbose:
                            components_info += f"\n• [{status_color}]{comp_name}[/{status_color}] - {comp_status} (ID: {comp_id})"
                        else:
                            components_info += f"\n• [{status_color}]{comp_name}[/{status_color}] - {comp_status}"

                # Incident Updates
                updates_info = ""
                if hasattr(incident, 'incident_updates') and incident.incident_updates:
                    updates_info = f"""

[bold cyan]Incident Updates ({len(incident.incident_updates)}):[/bold cyan]"""
                    for i, update in enumerate(incident.incident_updates, 1):
                        if isinstance(update, dict):
                            update_body = update.get('body', '')
                            update_status = update.get('status', 'unknown')
                            update_created = update.get('created_at', '')
                            update_id = update.get('id', '')
                        else:
                            update_body = getattr(update, 'body', '')
                            update_status = getattr(update, 'status', 'unknown')
                            update_created = getattr(update, 'created_at', '')
                            update_id = getattr(update, 'id', '')
                        
                        # Format timestamp
                        try:
                            if isinstance(update_created, str):
                                from dateutil import parser
                                dt = parser.parse(update_created)
                                time_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                            else:
                                time_str = str(update_created)
                        except:
                            time_str = str(update_created)
                        
                        updates_info += f"\n\n[bold]Update #{i}[/bold] - [yellow]{update_status}[/yellow] at [dim]{time_str}[/dim]"
                        if self.verbose:
                            updates_info += f"\n[dim]ID: {update_id}[/dim]"
                        updates_info += f"\n{update_body}"

                # Postmortem
                postmortem_info = ""
                if hasattr(incident, 'postmortem_body') and incident.postmortem_body:
                    postmortem_info = f"""

[bold cyan]Postmortem:[/bold cyan]
{incident.postmortem_body}"""
                    if hasattr(incident, 'postmortem_published_at') and incident.postmortem_published_at:
                        postmortem_info += f"\n[dim]Published: {incident.postmortem_published_at}[/dim]"

                # Timestamps
                timestamps = f"""

[bold cyan]Timestamps:[/bold cyan]
• Created: [white]{incident.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(incident, 'created_at') and incident.created_at else 'Unknown'}[/white]
• Updated: [white]{incident.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(incident, 'updated_at') and incident.updated_at else 'Unknown'}[/white]"""

                if hasattr(incident, 'resolved_at') and incident.resolved_at:
                    timestamps += f"""
• Resolved: [white]{incident.resolved_at}[/white]"""
                
                if hasattr(incident, 'monitoring_at') and incident.monitoring_at:
                    timestamps += f"""
• Monitoring: [white]{incident.monitoring_at.strftime('%Y-%m-%d %H:%M:%S UTC') if not isinstance(incident.monitoring_at, str) else incident.monitoring_at}[/white]"""

                full_info = f"{basic_info}{components_info}{updates_info}{postmortem_info}{timestamps}"

                panel = Panel(
                    full_info,
                    title=f"🚨 Incident: {incident.name}",
                    border_style="red",
                    padding=(1, 2),
                )

                self.console.print(panel)

        except Exception as e:
            self.display_error(f"Failed to get incident: {str(e)}")
            raise typer.Exit(1)

    def create_incident(
        self,
        page_id: str,
        name: str,
        status: str,
        body: Optional[str] = None,
        impact: Optional[str] = None,
        components: Optional[dict] = None,
        deliver_notifications: bool = True,
    ):
        """Create a new incident"""
        try:
            incidents_api = self.get_client()

            # Build incident data
            incident_data = {
                "name": name,
                "status": status,
                "deliver_notifications": deliver_notifications,
            }

            # Add optional fields
            if body:
                incident_data["body"] = body
            if impact:
                incident_data["impact"] = impact
            if components:
                incident_data["components"] = components

            # Create the incident
            incident = incidents_api.v1_pages_page_id_incidents_post(
                page_id=page_id,
                incident_create=incident_data
            )

            # Build success message
            success_details = [
                f"ID: {incident.id}",
                f"Name: {name}",
                f"Status: {status}",
                f"Impact: {impact or 'none'}"
            ]
            
            if components:
                success_details.append(f"Affected components: {len(components)}")

            self.display_success(
                f"Incident '{name}' created successfully!\n" + "\n".join(success_details),
                "✅ Incident Created"
            )

        except Exception as e:
            self.display_error(f"Failed to create incident: {str(e)}")
            raise typer.Exit(1)

    def update_incident(
        self,
        page_id: str,
        incident_id: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        body: Optional[str] = None,
        impact: Optional[str] = None,
        components: Optional[dict] = None,
    ):
        """Update an existing incident"""
        try:
            incidents_api = self.get_client()

            # Build incident data with only provided fields
            incident_data = {}

            if name is not None:
                incident_data["name"] = name
            if status is not None:
                incident_data["status"] = status
            if body is not None:
                incident_data["body"] = body
            if impact is not None:
                incident_data["impact"] = impact
            if components is not None:
                incident_data["components"] = components

            if not incident_data:
                self.display_error("No fields provided to update")
                raise typer.Exit(1)

            # Update the incident
            incident = incidents_api.v1_pages_page_id_incidents_incident_id_patch(
                page_id=page_id,
                incident_id=incident_id,
                incident_update_schema_edit=incident_data
            )

            self.display_success(
                f"Incident '{incident_id}' updated successfully!",
                "✅ Incident Updated"
            )

        except Exception as e:
            self.display_error(f"Failed to update incident: {str(e)}")
            raise typer.Exit(1)

    def delete_incident(self, page_id: str, incident_id: str, confirm: bool = False):
        """Delete an incident"""
        try:
            if not confirm:
                if not Confirm.ask(f"Are you sure you want to delete incident {incident_id}? This action cannot be undone."):
                    self.console.print("[yellow]Operation cancelled.[/yellow]")
                    return

            incidents_api = self.get_client()
            incidents_api.v1_pages_page_id_incidents_incident_id_delete(
                page_id=page_id,
                incident_id=incident_id
            )

            self.display_success(
                f"Incident {incident_id} deleted successfully!",
                "✅ Incident Deleted"
            )

        except Exception as e:
            self.display_error(f"Failed to delete incident: {str(e)}")
            raise typer.Exit(1)


# Create Typer app for incidents commands
app = typer.Typer(name="incidents", help="🚨 Manage status page incidents", no_args_is_help=True)


@app.command("list")
def list_incidents(
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    component_id: Optional[str] = typer.Option(None, "--component-id", "-c", help="Filter by component ID"),
    unresolved: bool = typer.Option(False, "--unresolved", "-u", help="Show only unresolved incidents"),
    maintenance: bool = typer.Option(False, "--maintenance", "-m", help="Show only scheduled maintenance"),
):
    """List incidents for a status page"""
    from ..utils.config import get_output_format
    incidents_cmd = IncidentsCommand(get_output_format())
    incidents_cmd.list_incidents(page_id, component_id, unresolved, maintenance)


@app.command("get")
def get_incident(
    incident_id: str = typer.Argument(..., help="Incident ID to retrieve"),
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information including component and update IDs"),
):
    """Get specific incident details"""
    from ..utils.config import get_output_format
    incidents_cmd = IncidentsCommand(get_output_format(), verbose=verbose)
    incidents_cmd.get_incident(page_id, incident_id)


@app.command("create")
def create_incident(
    name: str = typer.Option(..., "--name", "-n", help="Incident name/title"),
    status: str = typer.Option(..., "--status", "-s", help="Incident status (investigating, identified, monitoring, resolved)"),
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Incident description/body"),
    impact: Optional[str] = typer.Option(None, "--impact", "-i", help="Impact level (none, minor, major, critical)"),
    components: Optional[str] = typer.Option(None, "--components", "-c", help="Components as JSON (e.g., '{\"component_id\":\"status\"}'). Valid statuses: operational, degraded_performance, partial_outage, major_outage, under_maintenance"),
    no_notifications: bool = typer.Option(False, "--no-notifications", help="Don't send notifications"),
):
    """Create a new incident"""
    import json
    from ..utils.config import get_output_format
    
    # Parse components if provided
    components_dict = None
    if components:
        try:
            components_dict = json.loads(components)
        except json.JSONDecodeError as e:
            from rich.console import Console
            console = Console()
            console.print(f"[red]Error parsing components JSON: {e}[/red]")
            raise typer.Exit(1)
    
    incidents_cmd = IncidentsCommand(get_output_format())
    incidents_cmd.create_incident(
        page_id=page_id,
        name=name,
        status=status,
        body=body,
        impact=impact,
        components=components_dict,
        deliver_notifications=not no_notifications,
    )


@app.command("update")
def update_incident(
    incident_id: str = typer.Argument(..., help="Incident ID to update"),
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Incident name/title"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Incident status"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Incident description/body"),
    impact: Optional[str] = typer.Option(None, "--impact", "-i", help="Impact level"),
    components: Optional[str] = typer.Option(None, "--components", "-c", help="Components as JSON (e.g., '{\"component_id\":\"status\"}'). Valid statuses: operational, degraded_performance, partial_outage, major_outage, under_maintenance"),
):
    """Update an existing incident"""
    import json
    from ..utils.config import get_output_format
    
    # Parse components if provided
    components_dict = None
    if components:
        try:
            components_dict = json.loads(components)
        except json.JSONDecodeError as e:
            from rich.console import Console
            console = Console()
            console.print(f"[red]Error parsing components JSON: {e}[/red]")
            raise typer.Exit(1)
    
    incidents_cmd = IncidentsCommand(get_output_format())
    incidents_cmd.update_incident(
        page_id=page_id,
        incident_id=incident_id,
        name=name,
        status=status,
        body=body,
        impact=impact,
        components=components_dict,
    )


@app.command("delete")
def delete_incident(
    incident_id: str = typer.Argument(..., help="Incident ID to delete"),
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
):
    """Delete an incident"""
    from ..utils.config import get_output_format
    incidents_cmd = IncidentsCommand(get_output_format())
    incidents_cmd.delete_incident(page_id, incident_id, confirm)



@app.command("unresolved")
def list_unresolved_incidents(
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    component_id: Optional[str] = typer.Option(None, "--component-id", "-c", help="Filter by component ID"),
):
    """List unresolved incidents (not resolved)"""
    from ..utils.config import get_output_format
    incidents_cmd = IncidentsCommand(get_output_format())
    incidents_cmd.list_incidents(page_id, component_id, unresolved=True)


@app.command("maintenance")
def list_maintenance_windows(
    page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
    component_id: Optional[str] = typer.Option(None, "--component-id", "-c", help="Filter by component ID"),
):
    """List scheduled maintenance windows"""
    from ..utils.config import get_output_format
    incidents_cmd = IncidentsCommand(get_output_format())
    incidents_cmd.list_incidents(page_id, component_id, maintenance=True)
