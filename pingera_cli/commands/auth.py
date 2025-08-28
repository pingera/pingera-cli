"""
Authentication commands for PingeraCLI
"""

import os
from typing import Optional

import typer
from rich.panel import Panel
from rich.prompt import Prompt

from .base import BaseCommand
from ..utils.config import get_config, save_config, get_api_key, set_api_key


class AuthCommand(BaseCommand):
    """
    Authentication command handler
    """

    def __init__(self):
        super().__init__()
        self.app = typer.Typer(
            name="auth",
            help="🔐 Manage authentication settings\n\n💡 Get your API key at: https://app.pingera.ru",
            no_args_is_help=True,
        )

        # Register commands
        self.app.command("login")(self.login)
        self.app.command("status")(self.status)
        self.app.command("logout")(self.logout)

    def login(
        self,
        api_key: Optional[str] = typer.Option(None, "--api-key", help="Pingera API key"),
        interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
    ):
        """
        Login to Pingera by setting API key
        """
        try:
            # If no API key provided, empty, or whitespace-only, or interactive mode requested, prompt for it
            if not api_key or not api_key.strip() or interactive:
                try:
                    api_key = Prompt.ask(
                        "[bold blue]Enter your Pingera API key[/bold blue]",
                        password=True
                    )
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]⚠ Operation cancelled[/yellow]")
                    raise typer.Exit(1)

            # Validate API key after potentially getting it from prompt
            if not api_key or not api_key.strip():
                self.console.print("[red]API key cannot be empty[/red]")
                raise typer.Exit(1)

            if len(api_key.strip()) < 10:
                self.display_warning(
                    "API key seems too short. Please verify it's correct.",
                    "⚠️  Warning"
                )

            # Test the API key by making a simple request
            self.console.print("🔍 Validating API key...")

            validation_status = self._validate_api_key(api_key.strip())
            self.console.print(f"API Key Status: {validation_status}")

            if "[red]❌ Invalid or expired[/red]" in validation_status:
                self.console.print("[red]Please check your API key and try again.[/red]")
                raise typer.Exit(1)

            # Save API key to config
            if set_api_key(api_key.strip()):
                self.display_success(
                    f"✅ API key has been saved successfully!\n\n"
                    f"You can now use all Pingera CLI commands.\n"
                    f"Run [cyan]pngr auth status[/cyan] to verify your authentication.",
                    "🔐 Authentication Success"
                )
            else:
                self.console.print("[red]Failed to save API key to configuration file.[/red]")
                raise typer.Exit(1)

        except Exception as e:
            self.display_error(f"Login failed: {str(e)}")
            raise typer.Exit(1)

    def status(self):
        """
        Check current authentication status
        """
        try:
            # Check for API key in environment variable
            env_api_key = os.getenv('PINGERA_API_KEY')

            # Check for API key in config file
            config_api_key = get_api_key()

            # Determine which API key is being used
            active_api_key = env_api_key or config_api_key

            if active_api_key:
                # Mask the API key for display
                masked_key = active_api_key[:8] + "..." + active_api_key[-4:] if len(active_api_key) > 12 else "***"

                source = "environment variable" if env_api_key else "config file"

                status_content = f"""
[green]✅ Authenticated[/green]

API Key: ✓ Set ({masked_key})
Source: {source}
Status: [green]Active[/green]

[dim]Note: Environment variable takes precedence over config file.[/dim]
                """

                # Validate API key
                validation_status = self._validate_api_key(active_api_key)
                status_content += f"\nAPI Key Check: {validation_status}"

            else:
                status_content = """
[red]❌ Not Authenticated[/red]

API Key: ✗ Not set

[bold]To authenticate:[/bold]
• Run [cyan]pngr auth login --api-key YOUR_KEY[/cyan]
• Or run [cyan]pngr auth login --interactive[/cyan]
• Or set environment variable: [cyan]export PINGERA_API_KEY=your_key[/cyan]
                """

            panel = Panel(
                status_content.strip(),
                title="🔐 Authentication Status",
                border_style="green" if active_api_key else "red",
                padding=(1, 2),
            )

            self.console.print(panel)

        except Exception as e:
            self.display_error(f"Failed to check authentication status: {str(e)}")
            raise typer.Exit(1)

    def logout(
        self,
        confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
    ):
        """
        Clear stored credentials
        """
        try:
            # Check if there's anything to logout from
            config_api_key = get_api_key()
            env_api_key = os.getenv('PINGERA_API_KEY')

            if not config_api_key and not env_api_key:
                self.display_info(
                    "No stored credentials found. You are already logged out.",
                    "ℹ️  Info"
                )
                return

            # Warning about environment variable
            if env_api_key and not confirm:
                self.display_warning(
                    "API key is set via environment variable (PINGERA_API_KEY).\n"
                    "This command will only clear the config file.\n"
                    "To fully logout, also run: [cyan]unset PINGERA_API_KEY[/cyan]",
                    "⚠️  Environment Variable Detected"
                )

            # Confirmation prompt
            if not confirm:
                should_logout = self.prompt_confirmation(
                    "Are you sure you want to clear stored credentials?",
                    default=False
                )
                if not should_logout:
                    self.console.print("[yellow]Logout cancelled[/yellow]")
                    return

            # Clear API key from config
            config = get_config()
            if 'api_key' in config:
                del config['api_key']
                if save_config(config):
                    self.display_success(
                        "✅ Credentials cleared from configuration file.\n\n"
                        + ("Note: Environment variable PINGERA_API_KEY is still set." if env_api_key else "You have been logged out successfully."),
                        "🚪 Logout Success"
                    )
                else:
                    self.display_error("Failed to clear credentials from configuration file.")
                    raise typer.Exit(1)
            else:
                self.display_info("No credentials found in configuration file.")

        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠ Operation cancelled[/yellow]")
        except Exception as e:
            self.display_error(f"Logout failed: {str(e)}")
            raise typer.Exit(1)

    def _validate_api_key(self, api_key: str) -> str:
        """
        Validate API key by making a test request

        Args:
            api_key: The API key to validate

        Returns:
            str: Formatted status message
        """
        try:
            # Import here to avoid circular imports and handle missing SDK gracefully
            from pingera import ApiClient, Configuration
            from pingera.api import ChecksApi
            from pingera.exceptions import UnauthorizedException

            # Configure the client (same pattern as checks command)
            configuration = Configuration()
            configuration.host = "https://api.pingera.ru"
            configuration.api_key['apiKeyAuth'] = api_key

            # Create API client
            api_client = ApiClient(configuration)
            checks_api = ChecksApi(api_client)

            # Make a lightweight test request to validate the API key
            checks_api.v1_checks_get()

            return "[green]✅ Valid[/green]"

        except ImportError:
            return "[yellow]⚠ Cannot validate (Pingera SDK not available)[/yellow]"
        except UnauthorizedException:
            return "[red]❌ Invalid or expired[/red]"
        except Exception as e:
            # Handle other API errors gracefully
            error_msg = str(e).lower()
            if "network" in error_msg or "connection" in error_msg or "timeout" in error_msg:
                return "[yellow]⚠ Cannot validate (network error)[/yellow]"
            else:
                return f"[yellow]⚠ Cannot validate ({str(e)})[/yellow]"


# Create the auth command instance
auth_cmd = AuthCommand()