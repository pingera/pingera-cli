
"""
Pages commands for PingeraCLI
"""

import os
from typing import Optional
from datetime import datetime

import typer
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from .base import BaseCommand
from ..utils.config import get_api_key


class PagesCommand(BaseCommand):
    """
    Commands for managing status pages
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
            from pingera.api import StatusPagesApi
            from ..utils.config import get_config

            # Configure the client
            configuration = Configuration()
            configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return StatusPagesApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def list_pages(self, page: int = 1, page_size: int = 20):
        """List status pages"""
        try:
            pages_api = self.get_client()

            # Build parameters for the API call
            params = {
                "page": page,
                "page_size": page_size
            }

            # Make API call
            response = pages_api.v1_pages_get(**params)

            if not hasattr(response, 'pages') or not response.pages:
                if self.output_format in ['json', 'yaml']:
                    self.output_data({"pages": [], "total": 0, "message": "No pages found"})
                else:
                    self.display_info("No status pages found.")
                return

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                pages_data = []
                for page_obj in response.pages:
                    page_dict = {
                        "id": str(page_obj.id) if hasattr(page_obj, 'id') and page_obj.id else None,
                        "name": page_obj.name if hasattr(page_obj, 'name') and page_obj.name else None,
                        "subdomain": page_obj.subdomain if hasattr(page_obj, 'subdomain') and page_obj.subdomain else None,
                        "domain": page_obj.domain if hasattr(page_obj, 'domain') and page_obj.domain else None,
                        "url": page_obj.url if hasattr(page_obj, 'url') and page_obj.url else None,
                        "page_description": page_obj.page_description if hasattr(page_obj, 'page_description') and page_obj.page_description else None,
                        "viewers_must_be_team_members": page_obj.viewers_must_be_team_members if hasattr(page_obj, 'viewers_must_be_team_members') else None,
                        "created_at": page_obj.created_at.isoformat() if hasattr(page_obj, 'created_at') and page_obj.created_at else None,
                        "updated_at": page_obj.updated_at.isoformat() if hasattr(page_obj, 'updated_at') and page_obj.updated_at else None,
                    }
                    pages_data.append(page_dict)

                self.output_data({
                    "pages": pages_data,
                    "total": len(pages_data),
                    "page": page,
                    "page_size": page_size
                })
            else:
                # Create table for default output
                table = Table(title="Status Pages")
                table.add_column("ID", style="cyan", min_width=15)
                table.add_column("Name", style="green", min_width=20)
                table.add_column("Subdomain", style="blue", min_width=15)
                table.add_column("Domain", style="yellow", min_width=20)
                table.add_column("Visibility", style="magenta")
                table.add_column("Created", style="dim")

                for page_obj in response.pages:
                    # Extract page data
                    page_id = str(page_obj.id) if hasattr(page_obj, 'id') and page_obj.id else "-"
                    page_name = str(page_obj.name) if hasattr(page_obj, 'name') and page_obj.name else "-"
                    
                    # Subdomain
                    subdomain = str(page_obj.subdomain) if hasattr(page_obj, 'subdomain') and page_obj.subdomain else "-"
                    
                    # Domain
                    domain = str(page_obj.domain) if hasattr(page_obj, 'domain') and page_obj.domain else "-"
                    
                    # Visibility
                    is_private = page_obj.viewers_must_be_team_members if hasattr(page_obj, 'viewers_must_be_team_members') else False
                    visibility = "🔒 Private" if is_private else "🌐 Public"
                    
                    # Created date
                    created_display = "-"
                    if hasattr(page_obj, 'created_at') and page_obj.created_at:
                        try:
                            created_display = page_obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        except (AttributeError, TypeError):
                            created_display = str(page_obj.created_at)

                    table.add_row(
                        page_id,
                        page_name,
                        subdomain,
                        domain,
                        visibility,
                        created_display
                    )

                self.console.print(table)

                # Show result summary
                self.console.print(f"\n[dim]Found {len(response.pages)} pages on page {page}[/dim]")
                self.console.print(f"[dim]💡 View page details: pngr pages get <page-id>[/dim]")

        except Exception as e:
            self.display_error(f"Failed to list pages: {str(e)}")
            raise typer.Exit(1)

    def get_page(self, page_id: str):
        """Get specific page details"""
        try:
            pages_api = self.get_client()
            page = pages_api.v1_pages_page_id_get(page_id=page_id)

            # Prepare data for different output formats
            if self.output_format in ['json', 'yaml']:
                page_data = {
                    "id": str(page.id) if hasattr(page, 'id') and page.id else None,
                    "name": page.name if hasattr(page, 'name') and page.name else None,
                    "subdomain": page.subdomain if hasattr(page, 'subdomain') and page.subdomain else None,
                    "domain": page.domain if hasattr(page, 'domain') and page.domain else None,
                    "url": page.url if hasattr(page, 'url') and page.url else None,
                    "headline": page.headline if hasattr(page, 'headline') and page.headline else None,
                    "page_description": page.page_description if hasattr(page, 'page_description') and page.page_description else None,
                    "viewers_must_be_team_members": page.viewers_must_be_team_members if hasattr(page, 'viewers_must_be_team_members') else None,
                    "password_protected": page.password_protected if hasattr(page, 'password_protected') else None,
                    "time_zone": page.time_zone if hasattr(page, 'time_zone') and page.time_zone else None,
                    "language": page.language if hasattr(page, 'language') and page.language else None,
                    "created_at": page.created_at.isoformat() if hasattr(page, 'created_at') and page.created_at else None,
                    "updated_at": page.updated_at.isoformat() if hasattr(page, 'updated_at') and page.updated_at else None,
                }
                self.output_data(page_data)
            else:
                # Rich formatted output
                is_private = page.viewers_must_be_team_members if hasattr(page, 'viewers_must_be_team_members') else False
                visibility_status = "[red]🔒 Private[/red]" if is_private else "[green]🌐 Public[/green]"
                
                password_status = "[yellow]🔑 Password Protected[/yellow]" if (hasattr(page, 'password_protected') and page.password_protected) else "[dim]No password[/dim]"

                basic_info = f"""[bold cyan]Basic Information:[/bold cyan]
• ID: [white]{page.id}[/white]
• Name: [white]{page.name}[/white]
• Subdomain: [blue]{page.subdomain if hasattr(page, 'subdomain') and page.subdomain else 'Not set'}[/blue]
• Domain: [yellow]{page.domain if hasattr(page, 'domain') and page.domain else 'Not set'}[/yellow]
• Visibility: {visibility_status}
• Security: {password_status}"""

                # Content section
                content_info = f"""
[bold cyan]Content:[/bold cyan]
• Headline: [white]{page.headline if hasattr(page, 'headline') and page.headline else 'Not set'}[/white]
• Description: [white]{page.page_description if hasattr(page, 'page_description') and page.page_description else 'Not set'}[/white]
• Company URL: [white]{page.url if hasattr(page, 'url') and page.url else 'Not set'}[/white]"""

                # Settings section
                settings_info = f"""
[bold cyan]Settings:[/bold cyan]
• Timezone: [white]{page.time_zone if hasattr(page, 'time_zone') and page.time_zone else 'UTC'}[/white]
• Language: [white]{page.language if hasattr(page, 'language') and page.language else 'en'}[/white]
• Created: [white]{page.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(page, 'created_at') and page.created_at else 'Unknown'}[/white]
• Updated: [white]{page.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(page, 'updated_at') and page.updated_at else 'Unknown'}[/white]"""

                # Combine all sections
                full_info = f"{basic_info}{content_info}{settings_info}"

                panel = Panel(
                    full_info,
                    title=f"📄 Status Page: {page.name}",
                    border_style="blue",
                    padding=(1, 2),
                )

                self.console.print(panel)

        except Exception as e:
            self.display_error(f"Failed to get page: {str(e)}")
            raise typer.Exit(1)

    def create_page(self, name: str, subdomain: Optional[str] = None, description: Optional[str] = None, headline: Optional[str] = None, url: Optional[str] = None, public: bool = True, time_zone: Optional[str] = None):
        """Create a new status page"""
        try:
            import json
            pages_api = self.get_client()

            # Build page data
            page_data = {
                "name": name,
                "viewers_must_be_team_members": not public
            }

            # Add optional fields
            if subdomain:
                page_data["subdomain"] = subdomain
            if description:
                page_data["page_description"] = description
            if headline:
                page_data["headline"] = headline
            if url:
                page_data["url"] = url
            if time_zone:
                page_data["time_zone"] = time_zone

            # Create the page
            page = pages_api.v1_pages_post(page=page_data)

            # Build success message
            visibility = "Public" if public else "Private"
            success_details = [
                f"ID: {page.id}",
                f"Name: {name}",
                f"Visibility: {visibility}"
            ]
            if subdomain:
                success_details.append(f"Subdomain: {subdomain}")
            if hasattr(page, 'subdomain') and page.subdomain:
                success_details.append(f"URL: https://{page.subdomain}.pingera.ru")

            self.display_success(
                f"Status page '{name}' created successfully!\n" + "\n".join(success_details),
                "✅ Page Created"
            )

        except Exception as e:
            self.display_error(f"Failed to create page: {str(e)}")
            raise typer.Exit(1)

    def delete_page(self, page_id: str, confirm: bool = False):
        """Delete a status page"""
        try:
            if not confirm:
                if not Confirm.ask(f"Are you sure you want to delete page {page_id}? This action cannot be undone."):
                    self.console.print("[yellow]Operation cancelled.[/yellow]")
                    return

            pages_api = self.get_client()
            pages_api.v1_pages_page_id_delete(page_id=page_id)

            self.display_success(
                f"Page {page_id} deleted successfully!",
                "✅ Page Deleted"
            )

        except Exception as e:
            self.display_error(f"Failed to delete page: {str(e)}")
            raise typer.Exit(1)


# Create Typer app for pages commands
app = typer.Typer(name="pages", help="📄 Manage status pages", no_args_is_help=True)


@app.command("list")
def list_pages(
    page: int = typer.Option(1, "--page", "-p", help="Page number"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Items per page"),
):
    """List status pages"""
    from ..utils.config import get_output_format
    pages_cmd = PagesCommand(get_output_format())
    pages_cmd.list_pages(page, page_size)


@app.command("get")
def get_page(
    page_id: str = typer.Argument(..., help="Page ID to retrieve"),
):
    """Get specific page details"""
    from ..utils.config import get_output_format
    pages_cmd = PagesCommand(get_output_format())
    pages_cmd.get_page(page_id)


@app.command("create")
def create_page(
    name: str = typer.Option(..., "--name", "-n", help="Page name"),
    subdomain: Optional[str] = typer.Option(None, "--subdomain", "-s", help="Subdomain (e.g., 'mycompany' for mycompany.pingera.ru)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Page description"),
    headline: Optional[str] = typer.Option(None, "--headline", help="Page headline"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Company URL"),
    private: bool = typer.Option(False, "--private", help="Make page private (requires team membership)"),
    time_zone: Optional[str] = typer.Option(None, "--timezone", "-t", help="Timezone (e.g., 'America/New_York')"),
):
    """Create a new status page"""
    from ..utils.config import get_output_format
    pages_cmd = PagesCommand(get_output_format())
    pages_cmd.create_page(name, subdomain, description, headline, url, not private, time_zone)


@app.command("delete")
def delete_page(
    page_id: str = typer.Argument(..., help="Page ID to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
):
    """Delete a status page"""
    from ..utils.config import get_output_format
    pages_cmd = PagesCommand(get_output_format())
    pages_cmd.delete_page(page_id, confirm)
