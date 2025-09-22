
"""
Commands for managing check-secret associations
"""

import os
from typing import Optional, List

import typer
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from .base import BaseCommand
from ..utils.config import get_api_key, get_output_format
from ..utils.console import console


class CheckSecretsCommand(BaseCommand):
    """
    Commands for managing check-secret associations
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
            from pingera.api import CheckSecretsApi

            # Configure the client
            configuration = Configuration()
            configuration.host = "https://api.pingera.ru"
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            return CheckSecretsApi(api_client)
        except ImportError:
            self.display_error("Pingera SDK not installed. Install with: pip install pingera-sdk")
            raise typer.Exit(1)
        except Exception as e:
            self.display_error(f"Failed to initialize client: {str(e)}")
            raise typer.Exit(1)

    def list_check_secrets(self, check_id: str):
        """List all secrets associated with a check"""
        try:
            check_secrets_api = self.get_client()
            
            # Make API call
            secrets = check_secrets_api.v1_checks_check_id_secrets_get(check_id)
            
            # Handle different output formats
            if self.output_format in ['json', 'yaml']:
                # Convert to dict for JSON/YAML output
                secrets_data = [secret.to_dict() for secret in secrets]
                self.output_data({
                    'check_id': check_id,
                    'secrets': secrets_data,
                    'total': len(secrets_data)
                })
            else:
                # Table format
                if not secrets:
                    self.display_info(f"No secrets associated with check {check_id}")
                    return

                table = Table(title=f"Secrets for Check {check_id}")
                table.add_column("Association ID", style="cyan")
                table.add_column("Secret ID", style="yellow")
                table.add_column("Secret Name", style="white")
                table.add_column("Environment Variable", style="green")
                table.add_column("Created At", style="dim")

                for secret in secrets:
                    secret_name = secret.secret.secret_name if hasattr(secret, 'secret') and secret.secret else 'Unknown'
                    
                    table.add_row(
                        secret.id or '',
                        secret.secret_id or '',
                        secret_name,
                        secret.env_variable or '',
                        str(secret.created_at) if secret.created_at else ''
                    )

                console.print(table)
                console.print(f"\n[dim]Found {len(secrets)} secret associations[/dim]")

        except Exception as e:
            self.display_error(f"Failed to list check secrets: {str(e)}")
            raise typer.Exit(1)

    def add_secret_to_check(self, check_id: str, secret_id: str, env_variable: str):
        """Add a secret to a check with an environment variable name"""
        try:
            check_secrets_api = self.get_client()
            
            # Import the CheckSecret model
            from pingera.models import CheckSecret
            
            # Create the association
            check_secret = CheckSecret(
                secret_id=secret_id,
                env_variable=env_variable
            )
            
            # Make API call
            created_association = check_secrets_api.v1_checks_check_id_secrets_post(check_id, check_secret)
            
            # Handle different output formats
            if self.output_format in ['json', 'yaml']:
                self.output_data(created_association.to_dict())
            else:
                self.display_success(
                    f"Secret '{secret_id}' successfully associated with check '{check_id}' as environment variable '{env_variable}'"
                )
                
                # Show details table
                table = Table(title="Created Association")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="white")

                table.add_row("Association ID", created_association.id or '')
                table.add_row("Check ID", check_id)
                table.add_row("Secret ID", created_association.secret_id or '')
                table.add_row("Environment Variable", created_association.env_variable or '')
                table.add_row("Created At", str(created_association.created_at) if created_association.created_at else '')

                console.print(table)

        except Exception as e:
            self.display_error(f"Failed to add secret to check: {str(e)}")
            raise typer.Exit(1)

    def remove_secret_from_check(self, check_id: str, secret_id: str, force: bool = False):
        """Remove a secret association from a check"""
        try:
            check_secrets_api = self.get_client()
            
            # Confirmation prompt unless force is specified
            if not force:
                if not self.prompt_confirmation(
                    f"Are you sure you want to remove secret '{secret_id}' from check '{check_id}'?",
                    default=False
                ):
                    self.display_info("Operation cancelled")
                    return
            
            # Make API call
            check_secrets_api.v1_checks_check_id_secrets_secret_id_delete(check_id, secret_id)
            
            if self.output_format in ['json', 'yaml']:
                self.output_data({
                    "message": f"Secret '{secret_id}' removed from check '{check_id}'",
                    "check_id": check_id,
                    "secret_id": secret_id
                })
            else:
                self.display_success(f"Secret '{secret_id}' removed from check '{check_id}'")

        except Exception as e:
            self.display_error(f"Failed to remove secret from check: {str(e)}")
            raise typer.Exit(1)

    def update_all_secrets_for_check(self, check_id: str, associations: List[dict]):
        """Replace all secret associations for a check"""
        try:
            check_secrets_api = self.get_client()
            
            # Import the CheckSecret model
            from pingera.models import CheckSecret
            
            # Create CheckSecret objects from the associations
            check_secrets = []
            for assoc in associations:
                check_secret = CheckSecret(
                    secret_id=assoc['secret_id'],
                    env_variable=assoc['env_variable']
                )
                check_secrets.append(check_secret)
            
            # Make API call
            updated_associations = check_secrets_api.v1_checks_check_id_secrets_put(check_id, check_secrets)
            
            # Handle different output formats
            if self.output_format in ['json', 'yaml']:
                associations_data = [assoc.to_dict() for assoc in updated_associations]
                self.output_data({
                    'check_id': check_id,
                    'secrets': associations_data,
                    'total': len(associations_data)
                })
            else:
                self.display_success(f"Updated all secret associations for check '{check_id}'")
                
                if updated_associations:
                    table = Table(title=f"Updated Associations for Check {check_id}")
                    table.add_column("Association ID", style="cyan")
                    table.add_column("Secret ID", style="yellow")
                    table.add_column("Environment Variable", style="green")

                    for assoc in updated_associations:
                        table.add_row(
                            assoc.id or '',
                            assoc.secret_id or '',
                            assoc.env_variable or ''
                        )

                    console.print(table)
                    console.print(f"\n[dim]Total associations: {len(updated_associations)}[/dim]")
                else:
                    console.print("[dim]No associations remaining[/dim]")

        except Exception as e:
            self.display_error(f"Failed to update check secrets: {str(e)}")
            raise typer.Exit(1)


# Create Typer app for check secrets commands
app = typer.Typer(name="secrets", help="Manage secrets for checks")


@app.command("list")
def list_secrets(
    check_id: str = typer.Argument(..., help="Check ID to list secrets for"),
):
    """List all secrets associated with a check"""
    check_secrets_cmd = CheckSecretsCommand(get_output_format())
    check_secrets_cmd.list_check_secrets(check_id)


@app.command("add")
def add_secret(
    check_id: str = typer.Argument(..., help="Check ID to add secret to"),
    secret_id: str = typer.Argument(..., help="Secret ID to associate"),
    env_variable: str = typer.Argument(..., help="Environment variable name for the secret"),
):
    """Add a secret to a check with an environment variable name"""
    if len(env_variable) > 100:
        console.print("[red]Error:[/red] Environment variable name must be 100 characters or less")
        raise typer.Exit(1)
    
    check_secrets_cmd = CheckSecretsCommand(get_output_format())
    check_secrets_cmd.add_secret_to_check(check_id, secret_id, env_variable)


@app.command("remove")
def remove_secret(
    check_id: str = typer.Argument(..., help="Check ID to remove secret from"),
    secret_id: str = typer.Argument(..., help="Secret ID to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Remove a secret association from a check"""
    check_secrets_cmd = CheckSecretsCommand(get_output_format())
    check_secrets_cmd.remove_secret_from_check(check_id, secret_id, force)


@app.command("update-all")
def update_all_secrets(
    check_id: str = typer.Argument(..., help="Check ID to update secrets for"),
    associations_json: str = typer.Option(..., "--associations", help="JSON array of secret associations: '[{\"secret_id\": \"sec123\", \"env_variable\": \"VAR_NAME\"}]'"),
):
    """Replace all secret associations for a check"""
    import json
    
    try:
        associations = json.loads(associations_json)
        if not isinstance(associations, list):
            console.print("[red]Error:[/red] Associations must be a JSON array")
            raise typer.Exit(1)
        
        # Validate each association
        for i, assoc in enumerate(associations):
            if not isinstance(assoc, dict):
                console.print(f"[red]Error:[/red] Association {i+1} must be an object")
                raise typer.Exit(1)
            if 'secret_id' not in assoc or 'env_variable' not in assoc:
                console.print(f"[red]Error:[/red] Association {i+1} must have 'secret_id' and 'env_variable' fields")
                raise typer.Exit(1)
            if len(assoc['env_variable']) > 100:
                console.print(f"[red]Error:[/red] Environment variable name in association {i+1} must be 100 characters or less")
                raise typer.Exit(1)
        
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON: {str(e)}")
        console.print("[dim]Example: '[{\"secret_id\": \"sec123abc456\", \"env_variable\": \"DATABASE_PASSWORD\"}]'[/dim]")
        raise typer.Exit(1)
    
    check_secrets_cmd = CheckSecretsCommand(get_output_format())
    check_secrets_cmd.update_all_secrets_for_check(check_id, associations)
