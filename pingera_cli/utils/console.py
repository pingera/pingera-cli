"""
Console utilities for rich output formatting
"""

from rich.console import Console
from rich.theme import Theme

# Define custom theme for consistent styling
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
    "error": "bold red on white",
    "highlight": "bold yellow",
    "primary": "bold blue",
    "secondary": "dim white",
})

# Main console for standard output
console = Console(
    theme=custom_theme,
    highlight=True,
    markup=True,
    emoji=True,
    width=None,  # Auto-detect terminal width
)

# Error console for error messages
error_console = Console(
    stderr=True,
    theme=custom_theme,
    highlight=True,
    markup=True,
    emoji=True,
    width=None,
)

def print_banner():
    """
    Print a welcome banner for PingeraCLI
    """
    banner = """
[bold blue]
██████╗ ██╗███╗   ██╗ ██████╗ ███████╗██████╗  █████╗      ██████╗██╗     ██╗
██╔══██╗██║████╗  ██║██╔════╝ ██╔════╝██╔══██╗██╔══██╗    ██╔════╝██║     ██║
██████╔╝██║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝███████║    ██║     ██║     ██║
██╔═══╝ ██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗██╔══██║    ██║     ██║     ██║
██║     ██║██║ ╚████║╚██████╔╝███████╗██║  ██║██║  ██║    ╚██████╗███████╗██║
╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝
[/bold blue]
    """
    console.print(banner)
    console.print("[dim]A beautiful CLI tool for Pingera Platform[/dim]\n")


def print_separator(char: str = "─", length: int = 50, style: str = "dim"):
    """
    Print a separator line
    
    Args:
        char: Character to use for separator
        length: Length of the separator
        style: Rich style to apply
    """
    separator = char * length
    console.print(f"[{style}]{separator}[/{style}]")


def print_status(message: str, status: str = "info"):
    """
    Print a status message with appropriate styling
    
    Args:
        message: The message to print
        status: Status type (info, warning, danger, success, error)
    """
    status_icons = {
        "info": "ℹ️",
        "warning": "⚠️",
        "danger": "🚨",
        "success": "✅",
        "error": "❌",
    }
    
    icon = status_icons.get(status, "•")
    console.print(f"[{status}]{icon} {message}[/{status}]")
