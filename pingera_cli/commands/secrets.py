
"""
Commands for managing organization secrets
"""

import os
import sys
from typing import Optional

import typer
from rich.table import Table

from .base import BaseCommand
from ..utils.config import get_api_key, get_output_format
from ..utils.console import console


class SecretsCommand(BaseCommand):
    """
    Commands for managing organization secrets
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
            from pingera.api import SecretsApi

            # Configure the client
            configuration = Configuration()
            configuration.host = "https://api.pingera.ru"
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return SecretsApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def list_secrets(self, page: int = 1, page_size: int = 20):
        """List organization secrets"""
        try:
            secrets_api = self.get_client()
            
            # Make API call
            response = secrets_api.v1_secrets_get(page=page, page_size=page_size)
            
            # Handle named tuple/object response with secrets and pagination attributes
            if hasattr(response, 'secrets'):
                secrets = response.secrets
                pagination = getattr(response, 'pagination', {})
            elif isinstance(response, (list, tuple)) and len(response) >= 2:
                secrets = response[0]
                pagination = response[1] if len(response) > 1 else {}
            else:
                secrets = response
                pagination = {}
            
            # Handle different output formats
            if self.output_format in ['json', 'yaml']:
                # Convert to dict for JSON/YAML output
                secrets_data = {
                    'secrets': [secret.to_dict() for secret in secrets],
                    'pagination': pagination if pagination else {
                        'page': page,
                        'page_size': page_size,
                        'total': len(secrets)
                    }
                }
                self.output_data(secrets_data)
            else:
                # Table format
                if not secrets:
                    self.display_info("No secrets found")
                    return

                table = Table(title="Organization Secrets")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="white")
                table.add_column("Created At", style="dim")
                table.add_column("Updated At", style="dim")
                table.add_column("Created By", style="dim")

                for secret in secrets:
                    table.add_row(
                        secret.id or '',
                        secret.secret_name or '',
                        str(secret.created_at) if secret.created_at else '',
                        str(secret.updated_at) if secret.updated_at else '',
                        secret.created_by or ''
                    )

                console.print(table)
                
                # Show pagination info
                if pagination and pagination.get('total_pages', 1) > 1:
                    current_page = pagination.get('page', page)
                    total_pages = pagination.get('total_pages', 1)
                    total_items = pagination.get('total_items', len(secrets))
                    console.print(f"\n[dim]Page {current_page} of {total_pages} ({total_items} total secrets)[/dim]")
                else:
                    console.print(f"\n[dim]Found {len(secrets)} secrets[/dim]")

        except Exception as e:
            self.display_error(f"Failed to list secrets: {str(e)}")
            raise typer.Exit(1)

    def get_secret(self, secret_id: str):
        """Get a specific secret by ID"""
        try:
            secrets_api = self.get_client()
            
            # Make API call
            secret = secrets_api.v1_secrets_secret_id_get(secret_id)
            
            # Handle different output formats
            if self.output_format in ['json', 'yaml']:
                self.output_data(secret.to_dict())
            else:
                # Table format
                table = Table(title=f"Secret Details: {secret.secret_name}")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="white")

                table.add_row("ID", secret.id or '')
                table.add_row("Name", secret.secret_name or '')
                
                # Show secret value if available (marked as sensitive)
                if hasattr(secret, 'secret_value') and secret.secret_value:
                    table.add_row("Value", f"[red]{'*' * 20}[/red] (hidden for security)")
                
                table.add_row("Created At", str(secret.created_at) if secret.created_at else '')
                table.add_row("Updated At", str(secret.updated_at) if secret.updated_at else '')
                table.add_row("Created By", secret.created_by or '')
                table.add_row("Updated By", secret.updated_by or '')

                console.print(table)

        except Exception as e:
            self.display_error(f"Failed to get secret: {str(e)}")
            raise typer.Exit(1)

    def create_secret(self, name: str, value: str):
        """Create a new secret"""
        try:
            secrets_api = self.get_client()
            
            # Import the Secret model
            from pingera.models import Secret1
            
            # Create secret object
            secret_data = Secret1(
                secret_name=name,
                secret_value=value
            )
            
            # Make API call
            created_secret = secrets_api.v1_secrets_post(secret_data)
            
            # Handle different output formats
            if self.output_format in ['json', 'yaml']:
                self.output_data(created_secret.to_dict())
            else:
                self.display_success(f"Secret '{name}' created successfully with ID: {created_secret.id}")
                
                # Show details table
                table = Table(title="Created Secret")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="white")

                table.add_row("ID", created_secret.id or '')
                table.add_row("Name", created_secret.secret_name or '')
                table.add_row("Created At", str(created_secret.created_at) if created_secret.created_at else '')

                console.print(table)

        except Exception as e:
            self.display_error(f"Failed to create secret: {str(e)}")
            raise typer.Exit(1)

    def update_secret(self, secret_id: str, value: str):
        """Update an existing secret"""
        try:
            secrets_api = self.get_client()
            
            # Import the Secret model for update
            from pingera.models import Secret2
            
            # Create update object (only value can be updated)
            secret_update = Secret2(secret_value=value)
            
            # Make API call
            updated_secret = secrets_api.v1_secrets_secret_id_patch(secret_id, secret_update)
            
            # Handle different output formats
            if self.output_format in ['json', 'yaml']:
                self.output_data(updated_secret.to_dict())
            else:
                self.display_success(f"Secret '{updated_secret.secret_name}' updated successfully")
                
                # Show details table
                table = Table(title="Updated Secret")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="white")

                table.add_row("ID", updated_secret.id or '')
                table.add_row("Name", updated_secret.secret_name or '')
                table.add_row("Updated At", str(updated_secret.updated_at) if updated_secret.updated_at else '')

                console.print(table)

        except Exception as e:
            self.display_error(f"Failed to update secret: {str(e)}")
            raise typer.Exit(1)

    def delete_secret(self, secret_id: str, force: bool = False):
        """Delete a secret"""
        try:
            secrets_api = self.get_client()
            
            # Get secret details first for confirmation
            try:
                secret = secrets_api.v1_secrets_secret_id_get(secret_id)
                secret_name = secret.secret_name
            except Exception:
                secret_name = secret_id
            
            # Confirmation prompt unless force is specified
            if not force:
                if not self.prompt_confirmation(
                    f"Are you sure you want to delete secret '{secret_name}'? This action cannot be undone.",
                    default=False
                ):
                    self.display_info("Operation cancelled")
                    return
            
            # Make API call
            secrets_api.v1_secrets_secret_id_delete(secret_id)
            
            if self.output_format in ['json', 'yaml']:
                self.output_data({"message": f"Secret '{secret_name}' deleted successfully", "secret_id": secret_id})
            else:
                self.display_success(f"Secret '{secret_name}' deleted successfully")

        except Exception as e:
            self.display_error(f"Failed to delete secret: {str(e)}")
            raise typer.Exit(1)


# Create Typer app for secrets commands
app = typer.Typer(name="secrets", help="Manage organization secrets")


@app.command("list")
def list_secrets(
    page: int = typer.Option(1, "--page", "-p", help="Page number (default: 1)"),
    page_size: int = typer.Option(20, "--page-size", "-s", help="Number of items per page (default: 20, max: 100)"),
):
    """List all organization secrets"""
    secrets_cmd = SecretsCommand(get_output_format())
    secrets_cmd.list_secrets(page, page_size)


@app.command("get")
def get_secret(
    secret_id: str = typer.Argument(..., help="Secret ID to retrieve"),
):
    """Get a specific secret by ID"""
    secrets_cmd = SecretsCommand(get_output_format())
    secrets_cmd.get_secret(secret_id)


@app.command("create")
def create_secret(
    name: str = typer.Argument(..., help="Secret name (max 100 characters)"),
    value: str = typer.Option(..., "--value", "-v", help="Secret value", prompt=True, hide_input=True),
):
    """Create a new secret"""
    if len(name) > 100:
        console.print("[red]Error:[/red] Secret name must be 100 characters or less")
        raise typer.Exit(1)
    
    secrets_cmd = SecretsCommand(get_output_format())
    secrets_cmd.create_secret(name, value)


@app.command("update")
def update_secret(
    secret_id: str = typer.Argument(..., help="Secret ID to update"),
    value: str = typer.Option(..., "--value", "-v", help="New secret value", prompt=True, hide_input=True),
):
    """Update an existing secret (only the value can be updated)"""
    secrets_cmd = SecretsCommand(get_output_format())
    secrets_cmd.update_secret(secret_id, value)


@app.command("delete")
def delete_secret(
    secret_id: str = typer.Argument(..., help="Secret ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Delete a secret (this action cannot be undone)"""
    secrets_cmd = SecretsCommand(get_output_format())
    secrets_cmd.delete_secret(secret_id, force)
