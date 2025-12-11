"""
Main CLI application entry point using typer framework
"""

import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import __version__
from .commands.base import BaseCommand
from .commands.auth import auth_cmd
from .commands.checks import app as checks_app
from .commands.secrets import app as secrets_app
from .commands.pages import app as pages_app
from .commands.on_demand_checks import app as on_demand_app
from .utils.console import console, error_console
from .utils.config import get_config

# Initialize the main Typer app
app = typer.Typer(
    name="pngr",
    help="🚀 pngr - a nice CLI for Pingera platform\n\n🌐 Web application: https://app.pingera.ru\n💡 Get the API key in the app first to use the CLI",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=False,
)

# Initialize base command handler
base_cmd = BaseCommand()

# Register command groups
app.add_typer(auth_cmd.app, name="auth")
app.add_typer(checks_app, name="checks")
app.add_typer(secrets_app, name="secrets")
app.add_typer(pages_app, name="pages")


# Quick command aliases (separate help section)
@app.command("ping", rich_help_panel="🚀 Quick Commands")
def ping_alias(
    host: str = typer.Argument(..., help="Host to ping"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Region to execute from (e.g., ru-central1)"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for result"),
):
    """Quick ICMP ping check"""
    from .commands.on_demand_checks import OnDemandChecksCommand
    from .utils.config import get_output_format, get_verbose_mode

    cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    cmd.execute_custom_check(
        url=None,
        check_type="icmp",
        host=host,
        port=None,
        timeout=None,
        name=f"Ping {host}",
        regions=region,
        parameters=None,
        pw_script_file=None,
        from_file=None,
        wait_for_result=not no_wait
    )


@app.command("scan", rich_help_panel="🚀 Quick Commands")
def scan_alias(
    host: str = typer.Argument(..., help="Host to scan"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Region to execute from (e.g., ru-central1)"),
    ports: Optional[str] = typer.Option(None, "--ports", help="Ports to scan (e.g., '80,443' or '1-1024')"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for result"),
):
    """Quick port scan check"""
    from .commands.on_demand_checks import OnDemandChecksCommand
    from .utils.config import get_output_format, get_verbose_mode

    cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    cmd.execute_custom_check(
        url=None,
        check_type="portscan",
        host=host,
        port=None,
        timeout=None,
        name=f"Port scan {host}",
        regions=region,
        parameters=None,
        pw_script_file=None,
        from_file=None,
        wait_for_result=not no_wait,
        ports=ports
    )


@app.command("web", rich_help_panel="🚀 Quick Commands")
def web_alias(
    url: str = typer.Argument(..., help="URL to check"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Region to execute from (e.g., ru-central1)"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for result"),
):
    """Quick web check"""
    from .commands.on_demand_checks import OnDemandChecksCommand
    from .utils.config import get_output_format, get_verbose_mode

    cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    cmd.execute_custom_check(
        url=url,
        check_type="web",
        host=None,
        port=None,
        timeout=None,
        name=f"Web check {url}",
        regions=region,
        parameters=None,
        pw_script_file=None,
        from_file=None,
        wait_for_result=not no_wait
    )


@app.command("api", rich_help_panel="🚀 Quick Commands")
def api_alias(
    url: str = typer.Argument(..., help="API endpoint URL to check"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Region to execute from (e.g., ru-central1)"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for result"),
):
    """Quick API check"""
    from .commands.on_demand_checks import OnDemandChecksCommand
    from .utils.config import get_output_format, get_verbose_mode

    cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    cmd.execute_custom_check(
        url=url,
        check_type="api",
        host=None,
        port=None,
        timeout=None,
        name=f"API check {url}",
        regions=region,
        parameters=None,
        pw_script_file=None,
        from_file=None,
        wait_for_result=not no_wait
    )


@app.command("ssl", rich_help_panel="🚀 Quick Commands")
def ssl_alias(
    target: str = typer.Argument(..., help="Host or URL to check SSL certificate"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Region to execute from (e.g., ru-central1)"),
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port number (e.g., 443)"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for result"),
):
    """Quick SSL certificate check"""
    from .commands.on_demand_checks import OnDemandChecksCommand
    from .utils.config import get_output_format, get_verbose_mode

    cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())

    # Detect if target is a URL or hostname
    if target.startswith('http://') or target.startswith('https://'):
        url = target
        host = None
    else:
        url = None
        host = target

    cmd.execute_custom_check(
        url=url,
        check_type="ssl",
        host=host,
        port=port,
        timeout=None,
        name=f"SSL check {target}",
        regions=region,
        parameters=None,
        pw_script_file=None,
        from_file=None,
        wait_for_result=not no_wait,
        ports=None
    )


@app.command("dns", rich_help_panel="🚀 Quick Commands")
def dns_alias(
    domain: str = typer.Argument(..., help="Domain to check DNS records"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Region to execute from (e.g., ru-central1)"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for result"),
):
    """Quick DNS check"""
    from .commands.on_demand_checks import OnDemandChecksCommand
    from .utils.config import get_output_format, get_verbose_mode

    cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    cmd.execute_custom_check(
        url=None,
        check_type="dns",
        host=domain,
        port=None,
        timeout=None,
        name=f"DNS check {domain}",
        regions=region,
        parameters=None,
        pw_script_file=None,
        from_file=None,
        wait_for_result=not no_wait
    )


@app.command("syn", rich_help_panel="🚀 Quick Commands")
def synthetic_alias(
    script_file: str = typer.Argument(..., help="Path to Playwright script file"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Region to execute from (e.g., ru-central1)"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for result"),
):
    """Quick synthetic check"""
    from .commands.on_demand_checks import OnDemandChecksCommand
    from .utils.config import get_output_format, get_verbose_mode

    cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    cmd.execute_custom_check(
        url=None,
        check_type="synthetic",
        host=None,
        port=None,
        timeout=None,
        name=f"Synthetic check",
        regions=region,
        parameters=None,
        pw_script_file=script_file,
        from_file=None,
        wait_for_result=not no_wait
    )


@app.command("multistep", rich_help_panel="🚀 Quick Commands")
def multistep_alias(
    script_file: str = typer.Argument(..., help="Path to Playwright script file"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Region to execute from (e.g., ru-central1)"),
    no_wait: bool = typer.Option(False, "--no-wait", help="Don't wait for result"),
):
    """Quick multistep check"""
    from .commands.on_demand_checks import OnDemandChecksCommand
    from .utils.config import get_output_format, get_verbose_mode

    cmd = OnDemandChecksCommand(get_output_format(), verbose=get_verbose_mode())
    cmd.execute_custom_check(
        url=None,
        check_type="multistep",
        host=None,
        port=None,
        timeout=None,
        name=f"Multistep check",
        regions=region,
        parameters=None,
        pw_script_file=script_file,
        from_file=None,
        wait_for_result=not no_wait
    )


@app.command("version")
def version():
    """
    Show pngr version information
    """
    version_text = Text(f"PingeraCLI v{__version__}", style="bold blue")

    panel = Panel(
        version_text,
        title="🔍 Version Info",
        border_style="blue",
        padding=(1, 2),
    )

    console.print(panel)

    # Additional system info
    console.print(f"[dim]Python: {sys.version.split()[0]}[/dim]")
    console.print(f"[dim]Platform: {sys.platform}[/dim]")


@app.command("info")
def info():
    """
    Show information about pngr and Pingera SDK
    """
    try:
        from pingera import ApiClient
        sdk_version = getattr(ApiClient, '__version__', 'Unknown')
        sdk_status = "[green]✓ Installed[/green]"
    except ImportError:
        sdk_version = "Not installed"
        sdk_status = "[red]✗ Not found[/red]"

    info_content = f"""
[bold blue]pngr[/bold blue] v{__version__}
A beautiful CLI tool for Pingera Platform

[bold]🌐 Pingera Platform:[/bold]
• Web Dashboard: [link=https://app.pingera.ru]https://app.pingera.ru[/link]
• Documentation: [link=https://docs.pingera.ru]https://docs.pingera.ru[/link]
• Monitor uptime, performance, and availability of your services

[bold]📦 Dependencies:[/bold]
• Pingera SDK: {sdk_status} ({sdk_version})
• Typer: [green]✓ Installed[/green]
• Rich: [green]✓ Installed[/green]

[bold]🔧 Configuration:[/bold]
• Config file: {get_config().get('config_path', 'Not found')}
• API Key: {'[green]✓ Set[/green]' if os.getenv('PINGERA_API_KEY') else '[yellow]⚠ Not set[/yellow]'}

[bold]📚 Usage:[/bold]
Run [cyan]pngr --help[/cyan] to see available commands.
    """

    panel = Panel(
        info_content.strip(),
        title="ℹ️  System Information",
        border_style="cyan",
        padding=(1, 2),
    )

    console.print(panel)


@app.command("config")
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration"),
    set_api_key: Optional[str] = typer.Option(None, "--api-key", help="Set Pingera API key"),
    set_output_format: Optional[str] = typer.Option(None, "--output-format", help="Set output format (table, json, yaml)"),
    set_base_url: Optional[str] = typer.Option(None, "--base-url", help="Set Pingera API base URL"),
):
    """
    Manage pngr configuration
    """
    from .utils.config import set_output_format as save_output_format, get_config, save_config

    if set_api_key:
        # In a real implementation, this would save to a config file
        console.print(f"[yellow]Note:[/yellow] Set environment variable PINGERA_API_KEY={set_api_key}")
        console.print("[green]✓[/green] API key configuration noted. Please set as environment variable.")
        return

    if set_output_format:
        if set_output_format in ['table', 'json', 'yaml']:
            if save_output_format(set_output_format):
                console.print(f"[green]✓[/green] Output format set to: {set_output_format}")
            else:
                console.print(f"[red]✗[/red] Failed to save output format")
        else:
            console.print(f"[red]✗[/red] Invalid output format. Use: table, json, or yaml")
        return

    if set_base_url:
        config_data = get_config()
        config_data['base_url'] = set_base_url
        if save_config(config_data):
            console.print(f"[green]✓[/green] Base URL set to: {set_base_url}")
        else:
            console.print(f"[red]✗[/red] Failed to save base URL")
        return

    if show:
        config_data = get_config()

        config_content = f"""
[bold]🔧 Current Configuration:[/bold]

[bold]API Settings:[/bold]
• API Key: {'[green]✓ Set[/green]' if os.getenv('PINGERA_API_KEY') else '[red]✗ Not set[/red]'}
• Base URL: {config_data.get('base_url', 'https://api.pingera.ru')}

[bold]CLI Settings:[/bold]
• Output Format: {config_data.get('output_format', 'table')}
• Verbose Mode: {config_data.get('verbose', False)}
• Color Output: {config_data.get('color', True)}
        """

        panel = Panel(
            config_content.strip(),
            title="⚙️  Configuration",
            border_style="green",
            padding=(1, 2),
        )

        console.print(panel)
    else:
        console.print("[yellow]Use --show to display current configuration, --api-key to set API key, or --output-format to set output format[/yellow]")





@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    output: str = typer.Option("table", "--output", "-o", help="Output format: table, json, yaml"),
):
    """
    🚀 pngr - a nice CLI for Pingera platform

    Monitor your services, APIs, and websites with powerful uptime monitoring.
    Manage checks, view results, and get insights right from your terminal.

    🌐 Web Dashboard: https://app.pingera.ru
    📚 Documentation: https://docs.pingera.ru
    💡 Create an account at https://app.pingera.ru to get started with monitoring and get an API key

    Built with ❤️ using Typer and Rich for the best CLI experience.
    """
    if version:
        console.print(f"[bold blue]PingeraCLI[/bold blue] v{__version__}")
        raise typer.Exit()

    # If no command is provided and no version flag, show help
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()

    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")

    # Store current output format and verbose mode in config temporarily for subcommands
    from .utils.config import set_output_format as save_output_format, set_verbose_mode
    save_output_format(output)
    set_verbose_mode(verbose)


def cli_entry_point():
    """
    Entry point for the CLI application
    """
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        error_console.print(f"[red]Unexpected error:[/red] {str(e)}")
        sys.exit(1)


def main():
    """
    Main function for module execution
    """
    cli_entry_point()


if __name__ == "__main__":
    main()