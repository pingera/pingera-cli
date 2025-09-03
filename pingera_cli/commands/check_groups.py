
"""
Check groups commands for PingeraCLI
"""

from typing import Optional
from datetime import datetime

import typer
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from .base import BaseCommand
from ..utils.config import get_api_key


class CheckGroupsCommand(BaseCommand):
    """
    Commands for managing check groups
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
            from pingera.api import CheckGroupsApi

            # Configure the client
            configuration = Configuration()
            configuration.host = "https://api.pingera.ru"
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return CheckGroupsApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def list_groups(self, page: int = 1, page_size: int = 20):
        """List check groups"""
        try:
            groups_api = self.get_client()

            # Make API call using the actual SDK method
            response = groups_api.v1_check_groups_get(page=page, page_size=page_size)

            if not hasattr(response, 'groups') or not response.groups:
                if self.output_format == 'json':
                    self.output_data({"groups": [], "total": 0, "message": "No groups found"})
                elif self.output_format == 'yaml':
                    self.output_data({"groups": [], "total": 0, "message": "No groups found"})
                else:
                    self.display_info("No check groups found.")
                return

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                groups_data = []
                for group in response.groups:
                    group_dict = {
                        "id": str(group.id) if group.id else None,
                        "name": group.name if group.name else None,
                        "description": group.description if group.description else None,
                        "color": group.color if group.color else None,
                        "position": group.position if hasattr(group, 'position') else None,
                        "active": group.active if hasattr(group, 'active') else None,
                        "created_at": group.created_at.isoformat() if hasattr(group, 'created_at') and group.created_at else None,
                        "updated_at": group.updated_at.isoformat() if hasattr(group, 'updated_at') and group.updated_at else None
                    }
                    groups_data.append(group_dict)

                self.output_data({
                    "groups": groups_data,
                    "total": len(groups_data),
                    "page": page,
                    "page_size": page_size
                })
            else:
                # Create table for default output
                table = Table(title="Check Groups")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Description", style="white", max_width=30)
                table.add_column("Color", style="white", min_width=8)
                table.add_column("Position", style="blue")
                table.add_column("Active", style="magenta")
                table.add_column("Created", style="dim")

                for group in response.groups:
                    # Handle group data
                    group_id = str(group.id) if hasattr(group, 'id') and group.id else "-"
                    group_name = str(group.name) if hasattr(group, 'name') and group.name else "-"
                    
                    # Description with truncation
                    description = "-"
                    if hasattr(group, 'description') and group.description:
                        description = str(group.description)
                        if len(description) > 29:
                            description = description[:29] + "…"
                    
                    # Color display with preview
                    color_display = "-"
                    if hasattr(group, 'color') and group.color:
                        color_hex = group.color
                        color_display = f"[{color_hex}]●[/{color_hex}] {color_hex}"
                    
                    # Position
                    position = str(group.position) if hasattr(group, 'position') and group.position is not None else "-"
                    
                    # Active status
                    active_status = "✅" if hasattr(group, 'active') and group.active else "❌"
                    
                    # Created date
                    created_display = "-"
                    if hasattr(group, 'created_at') and group.created_at:
                        try:
                            created_display = group.created_at.strftime("%Y-%m-%d")
                        except (AttributeError, TypeError):
                            created_display = str(group.created_at)

                    table.add_row(
                        group_id,
                        group_name,
                        description,
                        color_display,
                        position,
                        active_status,
                        created_display
                    )

                self.console.print(table)
                self.console.print(f"\n[dim]Found {len(response.groups)} groups[/dim]")

        except Exception as e:
            self.display_error(f"Failed to list groups: {str(e)}")
            raise typer.Exit(1)

    def get_group(self, group_id: str):
        """Get specific check group details"""
        try:
            groups_api = self.get_client()
            group = groups_api.v1_check_groups_group_id_get(group_id=group_id)

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                group_data = {
                    "id": str(group.id) if group.id else None,
                    "name": group.name if group.name else None,
                    "description": group.description if group.description else None,
                    "color": group.color if group.color else None,
                    "position": group.position if hasattr(group, 'position') else None,
                    "active": group.active if hasattr(group, 'active') else None,
                    "created_at": group.created_at.isoformat() if hasattr(group, 'created_at') and group.created_at else None,
                    "updated_at": group.updated_at.isoformat() if hasattr(group, 'updated_at') and group.updated_at else None
                }
                self.output_data(group_data)
            else:
                # Rich formatted output for table format
                active_status = "[green]✓ Active[/green]" if hasattr(group, 'active') and group.active else "[red]✗ Inactive[/red]"
                
                # Color preview
                color_preview = ""
                if hasattr(group, 'color') and group.color:
                    color_preview = f"[{group.color}]●[/{group.color}] {group.color}"
                else:
                    color_preview = "[dim]No color set[/dim]"

                basic_info = f"""[bold cyan]Basic Information:[/bold cyan]
• ID: [white]{group.id}[/white]
• Name: [white]{group.name}[/white]
• Description: [white]{group.description if group.description else 'No description'}[/white]
• Color: {color_preview}
• Position: [white]{group.position if hasattr(group, 'position') and group.position is not None else 'Not set'}[/white]
• Active: {active_status}"""

                timing_info = f"""[bold cyan]Timestamps:[/bold cyan]
• Created: [white]{group.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(group, 'created_at') and group.created_at else 'Unknown'}[/white]
• Updated: [white]{group.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(group, 'updated_at') and group.updated_at else 'Unknown'}[/white]"""

                # Combine all sections
                full_info = f"{basic_info}\n\n{timing_info}"

                panel = Panel(
                    full_info,
                    title=f"📁 Check Group Details: {group.name}",
                    border_style="blue",
                    padding=(1, 2),
                )

                self.console.print(panel)

        except Exception as e:
            self.display_error(f"Failed to get group: {str(e)}")
            raise typer.Exit(1)

    def create_group(self, name: str, description: Optional[str] = None, color: Optional[str] = None, position: Optional[int] = None, active: bool = True):
        """Create a new check group"""
        try:
            groups_api = self.get_client()

            # Validate color format if provided
            if color:
                if not color.startswith('#'):
                    color = f"#{color}"
                if len(color) != 7:
                    self.display_error("Color must be a valid hex color code (e.g., #4F46E5)")
                    raise typer.Exit(1)

            # Build group data
            group_data = {
                "name": name,
                "active": active
            }

            if description:
                group_data["description"] = description
            if color:
                group_data["color"] = color
            if position is not None:
                group_data["position"] = position

            # Use the actual SDK method
            group = groups_api.v1_check_groups_post(check_group1=group_data)

            # Build success message
            success_details = [f"ID: {group.id}", f"Name: {name}"]
            if description:
                success_details.append(f"Description: {description}")
            if color:
                success_details.append(f"Color: {color}")
            if position is not None:
                success_details.append(f"Position: {position}")

            self.display_success(
                f"Check group '{name}' created successfully!\n" + "\n".join(success_details),
                "✅ Group Created"
            )

        except Exception as e:
            self.display_error(f"Failed to create group: {str(e)}")
            raise typer.Exit(1)

    def update_group(self, group_id: str, name: Optional[str] = None, description: Optional[str] = None, color: Optional[str] = None, position: Optional[int] = None, active: Optional[bool] = None):
        """Update an existing check group"""
        try:
            groups_api = self.get_client()

            # Validate color format if provided
            if color:
                if not color.startswith('#'):
                    color = f"#{color}"
                if len(color) != 7:
                    self.display_error("Color must be a valid hex color code (e.g., #4F46E5)")
                    raise typer.Exit(1)

            # Build update data
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if color is not None:
                update_data["color"] = color
            if position is not None:
                update_data["position"] = position
            if active is not None:
                update_data["active"] = active

            if not update_data:
                self.display_warning("No updates specified. Use --name, --description, --color, --position, or --active/--inactive to update.")
                return

            # Use the actual SDK method
            group = groups_api.v1_check_groups_group_id_patch(group_id=group_id, check_group2=update_data)

            status_msg = ""
            if active is not None:
                status_msg = f"\nStatus: {'Active' if active else 'Inactive'}"

            # Show what was updated
            updated_fields = []
            if name is not None:
                updated_fields.append(f"name: {group.name}")
            if description is not None:
                updated_fields.append(f"description: {group.description or 'cleared'}")
            if color is not None:
                updated_fields.append(f"color: {group.color}")
            if position is not None:
                updated_fields.append(f"position: {group.position}")

            update_summary = "\n".join([f"• {field}" for field in updated_fields]) if updated_fields else ""

            self.display_success(
                f"Check group {group_id} updated successfully!\n{update_summary}{status_msg}",
                "✅ Group Updated"
            )

        except Exception as e:
            self.display_error(f"Failed to update group: {str(e)}")
            raise typer.Exit(1)

    def delete_group(self, group_id: str, confirm: bool = False):
        """Delete a check group"""
        try:
            if not confirm:
                if not Confirm.ask(f"Are you sure you want to delete check group {group_id}? All checks in this group will be moved to ungrouped."):
                    self.console.print("[yellow]Operation cancelled.[/yellow]")
                    return

            groups_api = self.get_client()
            groups_api.v1_check_groups_group_id_delete(group_id=group_id)

            self.display_success(
                f"Check group {group_id} deleted successfully!\nAll checks from this group have been moved to ungrouped.",
                "✅ Group Deleted"
            )

        except Exception as e:
            self.display_error(f"Failed to delete group: {str(e)}")
            raise typer.Exit(1)

    def get_group_checks(self, group_id: str, page: int = 1, page_size: int = 20):
        """Get checks that belong to a specific group"""
        try:
            groups_api = self.get_client()
            
            # Make API call to get checks in group
            response = groups_api.v1_check_groups_group_id_checks_get(
                group_id=group_id,
                page=page,
                page_size=page_size
            )

            if not hasattr(response, 'checks') or not response.checks:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({"checks": [], "total": 0, "group_id": group_id, "message": "No checks found in this group"})
                else:
                    self.display_info(f"No checks found in group {group_id}.")
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
                        "active": check.active if hasattr(check, 'active') else None,
                        "interval": check.interval if check.interval else None,
                        "created_at": check.created_at.isoformat() if hasattr(check, 'created_at') and check.created_at else None
                    }
                    checks_data.append(check_dict)

                self.output_data({
                    "checks": checks_data,
                    "group_id": group_id,
                    "total": len(checks_data),
                    "page": page,
                    "page_size": page_size
                })
            else:
                # Create table for default output
                table = Table(title=f"Checks in Group {group_id}")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Type", style="blue")
                table.add_column("URL/Host", style="yellow")
                table.add_column("Active", style="magenta")
                table.add_column("Interval", style="white")
                table.add_column("Status", style="white")
                table.add_column("Created", style="dim")

                for check in response.checks:
                    # Convert all values to strings to avoid Rich rendering issues
                    check_id = str(check.id) if hasattr(check, 'id') and check.id else "-"
                    check_name = str(check.name) if hasattr(check, 'name') and check.name else "-"
                    check_type = str(check.type) if hasattr(check, 'type') and check.type else "-"

                    # Handle URL/Host display
                    check_url = "-"
                    if hasattr(check, 'url') and check.url:
                        check_url = str(check.url)
                    elif hasattr(check, 'host') and hasattr(check, 'port') and check.host and check.port:
                        check_url = f"{check.host}:{check.port}"

                    # Handle active status
                    active_status = "✅" if hasattr(check, 'active') and check.active else "❌"

                    # Handle interval
                    interval_display = f"{check.interval}s" if hasattr(check, 'interval') and check.interval else "-"

                    # Handle status
                    status_display = str(check.status) if hasattr(check, 'status') and check.status else "-"

                    # Handle created_at
                    created_display = "-"
                    if hasattr(check, 'created_at') and check.created_at:
                        try:
                            created_display = check.created_at.strftime("%Y-%m-%d")
                        except (AttributeError, TypeError):
                            created_display = str(check.created_at)

                    table.add_row(
                        check_id,
                        check_name,
                        check_type,
                        check_url,
                        active_status,
                        interval_display,
                        status_display,
                        created_display
                    )

                self.console.print(table)
                self.console.print(f"\n[dim]Found {len(response.checks)} checks in group {group_id}[/dim]")
                self.console.print(f"[dim]💡 Use 'pngr checks get <check-id>' for detailed check information[/dim]")

        except Exception as e:
            self.display_error(f"Failed to get group checks: {str(e)}")
            raise typer.Exit(1)


# Create Typer app for check groups commands
app = typer.Typer(name="groups", help="📁 Manage check groups", no_args_is_help=True)


def get_output_format():
    """Get output format from config"""
    from ..utils.config import get_config
    return get_config().get('output_format', 'table')


@app.command("list")
def list_groups(
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Items per page (max 100)"),
):
    """List check groups"""
    groups_cmd = CheckGroupsCommand(get_output_format())
    groups_cmd.list_groups(page, page_size)


@app.command("get")
def get_group(
    group_id: str = typer.Argument(..., help="Group ID to retrieve"),
):
    """Get specific check group details"""
    groups_cmd = CheckGroupsCommand(get_output_format())
    groups_cmd.get_group(group_id)


@app.command("create")
def create_group(
    name: str = typer.Option(..., "--name", "-n", help="Group name (max 100 characters)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Group description (max 500 characters)"),
    color: Optional[str] = typer.Option(None, "--color", "-c", help="Hex color code for the group (e.g., #4F46E5)"),
    position: Optional[int] = typer.Option(None, "--position", help="Position for ordering groups (0 = first)"),
    active: bool = typer.Option(True, "--active/--inactive", help="Whether the group is active"),
):
    """Create a new check group"""
    # Validate name length
    if len(name) > 100:
        typer.echo("Error: Group name cannot exceed 100 characters", err=True)
        raise typer.Exit(1)
    
    # Validate description length
    if description and len(description) > 500:
        typer.echo("Error: Group description cannot exceed 500 characters", err=True)
        raise typer.Exit(1)
    
    groups_cmd = CheckGroupsCommand(get_output_format())
    groups_cmd.create_group(name, description, color, position, active)


@app.command("update")
def update_group(
    group_id: str = typer.Argument(..., help="Group ID to update"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New group name (max 100 characters)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New group description (max 500 characters)"),
    color: Optional[str] = typer.Option(None, "--color", "-c", help="New hex color code (e.g., #4F46E5)"),
    position: Optional[int] = typer.Option(None, "--position", help="New position for ordering groups"),
    active: Optional[bool] = typer.Option(None, "--active/--inactive", help="Whether the group is active"),
):
    """Update an existing check group"""
    # Validate name length
    if name and len(name) > 100:
        typer.echo("Error: Group name cannot exceed 100 characters", err=True)
        raise typer.Exit(1)
    
    # Validate description length
    if description and len(description) > 500:
        typer.echo("Error: Group description cannot exceed 500 characters", err=True)
        raise typer.Exit(1)
    
    groups_cmd = CheckGroupsCommand(get_output_format())
    groups_cmd.update_group(group_id, name, description, color, position, active)


@app.command("delete")
def delete_group(
    group_id: str = typer.Argument(..., help="Group ID to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
):
    """Delete a check group. All checks in the group will be moved to ungrouped."""
    groups_cmd = CheckGroupsCommand(get_output_format())
    groups_cmd.delete_group(group_id, confirm)


@app.command("list-checks")
def get_group_checks(
    group_id: str = typer.Argument(..., help="Group ID to get checks for"),
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Items per page (max 100)"),
):
    """Get all checks that belong to a specific group"""
    groups_cmd = CheckGroupsCommand(get_output_format())
    groups_cmd.get_group_checks(group_id, page, page_size)
