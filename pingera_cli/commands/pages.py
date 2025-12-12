
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

    def create_page(
        self,
        name: str,
        subdomain: Optional[str] = None,
        domain: Optional[str] = None,
        description: Optional[str] = None,
        headline: Optional[str] = None,
        url: Optional[str] = None,
        support_url: Optional[str] = None,
        public: bool = True,
        password_protected: bool = False,
        time_zone: Optional[str] = None,
        language: Optional[str] = None,
        country: Optional[str] = None,
        hidden_from_search: bool = False,
        google_analytics_id: Optional[str] = None,
        yandex_metrica_id: Optional[str] = None,
        notifications_from_email: Optional[str] = None,
        notifications_email_footer: Optional[str] = None,
        allow_email_subscribers: bool = True,
        allow_sms_subscribers: bool = False,
        allow_webhook_subscribers: bool = False,
        allow_rss_atom_feeds: bool = True,
    ):
        """Create a new status page"""
        try:
            import json
            pages_api = self.get_client()

            # Build page data
            page_data = {
                "name": name,
                "viewers_must_be_team_members": not public,
                "password_protected": password_protected,
                "hidden_from_search": hidden_from_search,
                "allow_email_subscribers": allow_email_subscribers,
                "allow_sms_subscribers": allow_sms_subscribers,
                "allow_webhook_subscribers": allow_webhook_subscribers,
                "allow_rss_atom_feeds": allow_rss_atom_feeds,
            }

            # Add optional fields
            if subdomain:
                page_data["subdomain"] = subdomain
            if domain:
                page_data["domain"] = domain
            if description:
                page_data["page_description"] = description
            if headline:
                page_data["headline"] = headline
            if url:
                page_data["url"] = url
            if support_url:
                page_data["support_url"] = support_url
            if time_zone:
                page_data["time_zone"] = time_zone
            if language:
                page_data["language"] = language
            if country:
                page_data["country"] = country
            if google_analytics_id:
                page_data["google_analytics_id"] = google_analytics_id
            if yandex_metrica_id:
                page_data["yandex_metrica_id"] = yandex_metrica_id
            if notifications_from_email:
                page_data["notifications_from_email"] = notifications_from_email
            if notifications_email_footer:
                page_data["notifications_email_footer"] = notifications_email_footer

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

    def update_page(
        self,
        page_id: str,
        name: Optional[str] = None,
        subdomain: Optional[str] = None,
        domain: Optional[str] = None,
        description: Optional[str] = None,
        headline: Optional[str] = None,
        url: Optional[str] = None,
        support_url: Optional[str] = None,
        public: Optional[bool] = None,
        password_protected: Optional[bool] = None,
        time_zone: Optional[str] = None,
        language: Optional[str] = None,
        country: Optional[str] = None,
        hidden_from_search: Optional[bool] = None,
        google_analytics_id: Optional[str] = None,
        yandex_metrica_id: Optional[str] = None,
        notifications_from_email: Optional[str] = None,
        notifications_email_footer: Optional[str] = None,
        allow_email_subscribers: Optional[bool] = None,
        allow_sms_subscribers: Optional[bool] = None,
        allow_webhook_subscribers: Optional[bool] = None,
        allow_rss_atom_feeds: Optional[bool] = None,
    ):
        """Update an existing status page"""
        try:
            pages_api = self.get_client()

            # Build page data with only provided fields
            page_data = {}

            if name is not None:
                page_data["name"] = name
            if public is not None:
                page_data["viewers_must_be_team_members"] = not public
            if password_protected is not None:
                page_data["password_protected"] = password_protected
            if hidden_from_search is not None:
                page_data["hidden_from_search"] = hidden_from_search
            if allow_email_subscribers is not None:
                page_data["allow_email_subscribers"] = allow_email_subscribers
            if allow_sms_subscribers is not None:
                page_data["allow_sms_subscribers"] = allow_sms_subscribers
            if allow_webhook_subscribers is not None:
                page_data["allow_webhook_subscribers"] = allow_webhook_subscribers
            if allow_rss_atom_feeds is not None:
                page_data["allow_rss_atom_feeds"] = allow_rss_atom_feeds

            # Add optional fields only if provided
            if subdomain is not None:
                page_data["subdomain"] = subdomain
            if domain is not None:
                page_data["domain"] = domain
            if description is not None:
                page_data["page_description"] = description
            if headline is not None:
                page_data["headline"] = headline
            if url is not None:
                page_data["url"] = url
            if support_url is not None:
                page_data["support_url"] = support_url
            if time_zone is not None:
                page_data["time_zone"] = time_zone
            if language is not None:
                page_data["language"] = language
            if country is not None:
                page_data["country"] = country
            if google_analytics_id is not None:
                page_data["google_analytics_id"] = google_analytics_id
            if yandex_metrica_id is not None:
                page_data["yandex_metrica_id"] = yandex_metrica_id
            if notifications_from_email is not None:
                page_data["notifications_from_email"] = notifications_from_email
            if notifications_email_footer is not None:
                page_data["notifications_email_footer"] = notifications_email_footer

            if not page_data:
                self.display_error("No fields provided to update")
                raise typer.Exit(1)

            # Update the page
            page = pages_api.v1_pages_page_id_patch(page_id=page_id, page=page_data)

            # Build success message
            updated_fields = []
            if name is not None:
                updated_fields.append(f"Name: {name}")
            if subdomain is not None:
                updated_fields.append(f"Subdomain: {subdomain}")
            if public is not None:
                updated_fields.append(f"Visibility: {'Public' if public else 'Private'}")

            self.display_success(
                f"Status page '{page_id}' updated successfully!\n" + 
                (("\n".join(updated_fields)) if updated_fields else "Fields updated"),
                "✅ Page Updated"
            )

        except Exception as e:
            self.display_error(f"Failed to update page: {str(e)}")
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

    def get_client_optional_auth(self, require_auth: bool = False):
        """Get Pingera SDK client with optional authentication"""
        try:
            from pingera import ApiClient, Configuration
            from pingera.api import StatusPagesApi, StatusPagesIncidentsApi, StatusPagesComponentsApi
            from ..utils.config import get_config

            # Configure the client
            configuration = Configuration()
            configuration.host = get_config().get('base_url', 'https://api.pingera.ru')
            
            # Only add API key if required or available
            if require_auth:
                api_key = get_api_key()
                if not api_key:
                    self.display_error("API key not found. Use 'pngr auth login --api-key <key>' to set it.")
                    raise typer.Exit(1)
                configuration.api_key['apiKeyAuth'] = api_key
            else:
                # Try to get API key but don't fail if not available
                api_key = get_api_key()
                if api_key:
                    configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return {
                'pages': StatusPagesApi(api_client),
                'incidents': StatusPagesIncidentsApi(api_client),
                'components': StatusPagesComponentsApi(api_client)
            }
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def show_page_by_domain(self, domain: str):
        """Show page status by domain with incidents and components"""
        try:
            # Determine what to send to the API
            # If it ends with .pingera.ru, send only the subdomain
            # Otherwise, send the full domain
            if domain.endswith('.pingera.ru'):
                # Extract subdomain (everything before .pingera.ru)
                lookup_domain = domain.replace('.pingera.ru', '')
            else:
                lookup_domain = domain

            # Try without authentication first
            page = None
            clients = None
            try:
                clients = self.get_client_optional_auth(require_auth=False)
                page = clients['pages'].v1_pages_by_domain_domain_get(domain=lookup_domain)
            except Exception as e:
                # If it fails, try with authentication
                try:
                    clients = self.get_client_optional_auth(require_auth=True)
                    page = clients['pages'].v1_pages_by_domain_domain_get(domain=lookup_domain)
                except Exception as auth_error:
                    self.display_error(f"Failed to fetch page by domain '{domain}': {str(auth_error)}")
                    raise typer.Exit(1)

            if not page:
                self.display_error(f"Page not found for domain: {domain}")
                raise typer.Exit(1)

            page_id = str(page.id) if hasattr(page, 'id') else None
            
            # Fetch unresolved incidents
            unresolved_incidents = []
            try:
                all_incidents = clients['incidents'].v1_pages_page_id_incidents_get(page_id=page_id)
                if all_incidents:
                    for incident in all_incidents:
                        if hasattr(incident, 'status') and incident.status and incident.status != 'resolved':
                            unresolved_incidents.append(incident)
            except Exception:
                # Incidents might not be accessible, continue anyway
                pass

            # Fetch components
            components = []
            try:
                components = clients['components'].v1_pages_page_id_components_get(page_id=page_id)
                if not components:
                    components = []
            except Exception:
                # Components might not be accessible, continue anyway
                pass

            # Prepare output based on format
            if self.output_format in ['json', 'yaml']:
                # JSON/YAML output
                page_data = {
                    "page": {
                        "id": page_id,
                        "name": page.name if hasattr(page, 'name') else None,
                        "domain": domain,
                        "url": page.url if hasattr(page, 'url') and page.url else None,
                        "headline": page.headline if hasattr(page, 'headline') and page.headline else None,
                    },
                    "status": "operational" if len(unresolved_incidents) == 0 else "degraded",
                    "unresolved_incidents": [
                        {
                            "id": str(inc.id) if hasattr(inc, 'id') else None,
                            "name": inc.name if hasattr(inc, 'name') else None,
                            "status": inc.status if hasattr(inc, 'status') else None,
                            "impact": inc.impact if hasattr(inc, 'impact') else None,
                            "created_at": inc.created_at.isoformat() if hasattr(inc, 'created_at') and inc.created_at else None,
                        }
                        for inc in unresolved_incidents
                    ],
                    "components": [
                        {
                            "id": str(comp.id) if hasattr(comp, 'id') else None,
                            "name": comp.name if hasattr(comp, 'name') else None,
                            "status": comp.status if hasattr(comp, 'status') else None,
                            "description": comp.description if hasattr(comp, 'description') and comp.description else None,
                        }
                        for comp in components
                    ]
                }
                self.output_data(page_data)
            else:
                # Rich formatted output
                page_name = page.name if hasattr(page, 'name') else "Unknown"
                headline = page.headline if hasattr(page, 'headline') and page.headline else ""
                
                # Overall status
                if len(unresolved_incidents) == 0:
                    overall_status = "[green]✓ All Systems Operational[/green]"
                else:
                    overall_status = f"[red]⚠ {len(unresolved_incidents)} Active Incident{'s' if len(unresolved_incidents) > 1 else ''}[/red]"

                # Build page info
                page_info = f"""[bold cyan]Status Page:[/bold cyan]
• Name: [white]{page_name}[/white]
• Domain: [blue]{domain}[/blue]"""
                
                if headline:
                    page_info += f"\n• Headline: [white]{headline}[/white]"
                
                page_info += f"\n\n[bold cyan]Overall Status:[/bold cyan]\n{overall_status}"

                # Unresolved incidents section
                incidents_info = ""
                if unresolved_incidents:
                    incidents_info = f"\n\n[bold red]Active Incidents ({len(unresolved_incidents)}):[/bold red]"
                    for inc in unresolved_incidents:
                        inc_name = inc.name if hasattr(inc, 'name') else "Unknown"
                        inc_status = inc.status if hasattr(inc, 'status') else "unknown"
                        inc_impact = inc.impact if hasattr(inc, 'impact') else "unknown"
                        
                        impact_color = {
                            'none': 'green',
                            'minor': 'yellow',
                            'major': 'red',
                            'critical': 'bold red'
                        }.get(inc_impact, 'white')
                        
                        incidents_info += f"\n• [{impact_color}]{inc_name}[/{impact_color}] - {inc_status} (Impact: {inc_impact})"

                # Components section
                components_info = ""
                if components:
                    components_info = f"\n\n[bold cyan]Components ({len(components)}):[/bold cyan]"
                    for comp in components:
                        comp_name = comp.name if hasattr(comp, 'name') else "Unknown"
                        comp_status = comp.status if hasattr(comp, 'status') else "unknown"
                        
                        status_color = {
                            'operational': 'green',
                            'degraded_performance': 'yellow',
                            'partial_outage': 'yellow',
                            'major_outage': 'red',
                            'under_maintenance': 'blue'
                        }.get(comp_status, 'white')
                        
                        status_icon = {
                            'operational': '✓',
                            'degraded_performance': '⚠',
                            'partial_outage': '⚠',
                            'major_outage': '✗',
                            'under_maintenance': '🔧'
                        }.get(comp_status, '•')
                        
                        components_info += f"\n{status_icon} [{status_color}]{comp_name}[/{status_color}] - {comp_status}"
                else:
                    components_info = "\n\n[dim]No components configured[/dim]"

                # Combine all sections
                full_info = f"{page_info}{incidents_info}{components_info}"

                # Determine border color based on status
                border_color = "green" if len(unresolved_incidents) == 0 else "red"
                
                panel = Panel(
                    full_info,
                    title=f"📊 {page_name}",
                    border_style=border_color,
                    padding=(1, 2),
                )

                self.console.print(panel)
                
                # Add helpful hint
                self.console.print(f"\n[dim]💡 View past incidents: pngr pages incidents list -p {page_id}[/dim]")

        except typer.Exit:
            raise
        except Exception as e:
            self.display_error(f"Failed to show page: {str(e)}")
            raise typer.Exit(1)


# Create Typer app for pages commands
app = typer.Typer(name="pages", help="📄 Manage status pages", no_args_is_help=True)

# Import components and incidents apps to nest under pages
from . import components, incidents

# Add subcommands under pages
app.add_typer(components.app, name="components")
app.add_typer(incidents.app, name="incidents")


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
    domain: Optional[str] = typer.Option(None, "--domain", help="Custom domain"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Page description"),
    headline: Optional[str] = typer.Option(None, "--headline", help="Page headline"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Company URL"),
    support_url: Optional[str] = typer.Option(None, "--support-url", help="Support/contact page URL"),
    private: bool = typer.Option(False, "--private", help="Make page private (requires team membership)"),
    password_protected: bool = typer.Option(False, "--password-protected", help="Enable password protection"),
    time_zone: Optional[str] = typer.Option(None, "--timezone", "-t", help="Timezone (e.g., 'America/New_York')"),
    language: Optional[str] = typer.Option(None, "--language", help="Language code (e.g., 'en', 'ru')"),
    country: Optional[str] = typer.Option(None, "--country", help="Country"),
    hidden_from_search: bool = typer.Option(False, "--hidden-from-search", help="Hide from search engines"),
    google_analytics_id: Optional[str] = typer.Option(None, "--ga-id", help="Google Analytics ID"),
    yandex_metrica_id: Optional[str] = typer.Option(None, "--ym-id", help="Yandex Metrica ID"),
    notifications_from_email: Optional[str] = typer.Option(None, "--notifications-email", help="Notification sender email"),
    notifications_email_footer: Optional[str] = typer.Option(None, "--email-footer", help="Email notification footer"),
    allow_email_subscribers: bool = typer.Option(True, "--allow-email-subscribers/--no-email-subscribers", help="Allow email subscriptions"),
    allow_sms_subscribers: bool = typer.Option(False, "--allow-sms-subscribers", help="Allow SMS subscriptions"),
    allow_webhook_subscribers: bool = typer.Option(False, "--allow-webhook-subscribers", help="Allow webhook subscriptions"),
    allow_rss_atom_feeds: bool = typer.Option(True, "--allow-rss/--no-rss", help="Provide RSS/Atom feeds"),
):
    """Create a new status page"""
    from ..utils.config import get_output_format
    pages_cmd = PagesCommand(get_output_format())
    pages_cmd.create_page(
        name=name,
        subdomain=subdomain,
        domain=domain,
        description=description,
        headline=headline,
        url=url,
        support_url=support_url,
        public=not private,
        password_protected=password_protected,
        time_zone=time_zone,
        language=language,
        country=country,
        hidden_from_search=hidden_from_search,
        google_analytics_id=google_analytics_id,
        yandex_metrica_id=yandex_metrica_id,
        notifications_from_email=notifications_from_email,
        notifications_email_footer=notifications_email_footer,
        allow_email_subscribers=allow_email_subscribers,
        allow_sms_subscribers=allow_sms_subscribers,
        allow_webhook_subscribers=allow_webhook_subscribers,
        allow_rss_atom_feeds=allow_rss_atom_feeds,
    )


@app.command("update")
def update_page(
    page_id: str = typer.Argument(..., help="Page ID to update"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Page name"),
    subdomain: Optional[str] = typer.Option(None, "--subdomain", "-s", help="Subdomain (e.g., 'mycompany' for mycompany.pingera.ru)"),
    domain: Optional[str] = typer.Option(None, "--domain", help="Custom domain"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Page description"),
    headline: Optional[str] = typer.Option(None, "--headline", help="Page headline"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Company URL"),
    support_url: Optional[str] = typer.Option(None, "--support-url", help="Support/contact page URL"),
    public: Optional[bool] = typer.Option(None, "--public/--private", help="Make page public or private"),
    password_protected: Optional[bool] = typer.Option(None, "--password-protected/--no-password", help="Enable/disable password protection"),
    time_zone: Optional[str] = typer.Option(None, "--timezone", "-t", help="Timezone (e.g., 'America/New_York')"),
    language: Optional[str] = typer.Option(None, "--language", help="Language code (e.g., 'en', 'ru')"),
    country: Optional[str] = typer.Option(None, "--country", help="Country"),
    hidden_from_search: Optional[bool] = typer.Option(None, "--hidden-from-search/--visible-in-search", help="Hide/show in search engines"),
    google_analytics_id: Optional[str] = typer.Option(None, "--ga-id", help="Google Analytics ID"),
    yandex_metrica_id: Optional[str] = typer.Option(None, "--ym-id", help="Yandex Metrica ID"),
    notifications_from_email: Optional[str] = typer.Option(None, "--notifications-email", help="Notification sender email"),
    notifications_email_footer: Optional[str] = typer.Option(None, "--email-footer", help="Email notification footer"),
    allow_email_subscribers: Optional[bool] = typer.Option(None, "--allow-email-subscribers/--no-email-subscribers", help="Allow/disallow email subscriptions"),
    allow_sms_subscribers: Optional[bool] = typer.Option(None, "--allow-sms-subscribers/--no-sms-subscribers", help="Allow/disallow SMS subscriptions"),
    allow_webhook_subscribers: Optional[bool] = typer.Option(None, "--allow-webhook-subscribers/--no-webhook-subscribers", help="Allow/disallow webhook subscriptions"),
    allow_rss_atom_feeds: Optional[bool] = typer.Option(None, "--allow-rss/--no-rss", help="Provide/disable RSS/Atom feeds"),
):
    """Update an existing status page"""
    from ..utils.config import get_output_format
    pages_cmd = PagesCommand(get_output_format())
    pages_cmd.update_page(
        page_id=page_id,
        name=name,
        subdomain=subdomain,
        domain=domain,
        description=description,
        headline=headline,
        url=url,
        support_url=support_url,
        public=public,
        password_protected=password_protected,
        time_zone=time_zone,
        language=language,
        country=country,
        hidden_from_search=hidden_from_search,
        google_analytics_id=google_analytics_id,
        yandex_metrica_id=yandex_metrica_id,
        notifications_from_email=notifications_from_email,
        notifications_email_footer=notifications_email_footer,
        allow_email_subscribers=allow_email_subscribers,
        allow_sms_subscribers=allow_sms_subscribers,
        allow_webhook_subscribers=allow_webhook_subscribers,
        allow_rss_atom_feeds=allow_rss_atom_feeds,
    )


@app.command("delete")
def delete_page(
    page_id: str = typer.Argument(..., help="Page ID to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
):
    """Delete a status page"""
    from ..utils.config import get_output_format
    pages_cmd = PagesCommand(get_output_format())
    pages_cmd.delete_page(page_id, confirm)


@app.command("show")
def show_page_by_domain(
    domain: str = typer.Argument(..., help="Domain or subdomain (e.g., 'status.pingera.ru' or 'mystatus.example.com')"),
):
    """Show page status, incidents, and components by domain"""
    from ..utils.config import get_output_format
    pages_cmd = PagesCommand(get_output_format())
    pages_cmd.show_page_by_domain(domain)
