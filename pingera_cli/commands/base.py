"""
Base command class for PingeraCLI commands
"""

import json
from typing import Any, Dict, Optional
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..utils.console import console, error_console
from ..utils.config import get_config


class BaseCommand:
    """Base class for all CLI commands with common functionality"""

    def __init__(self, output_format: Optional[str] = None):
        self.console = console
        self.error_console = error_console
        self.output_format = output_format or get_config().get('output_format', 'table')

    def validate_api_key(self) -> str:
        """
        Validate that API key is available

        Returns:
            str: The API key

        Raises:
            ValueError: If API key is not found
        """
        api_key = os.getenv('PINGERA_API_KEY')
        if not api_key:
            raise ValueError("PINGERA_API_KEY environment variable not set")
        return api_key

    def validate_pingera_sdk(self):
        """
        Validate that Pingera SDK is installed and importable

        Raises:
            ImportError: If Pingera SDK is not available
        """
        try:
            from pingera import ApiClient, Configuration
            return (ApiClient, Configuration)
        except ImportError:
            raise ImportError("Pingera SDK not installed. Install with: pip install pingera-sdk")

    def display_success(self, message: str, title: str = "✅ Success"):
        """
        Display a success message in a panel

        Args:
            message: The success message to display
            title: Panel title (default: "✅ Success")
        """
        panel = Panel(
            message,
            title=title,
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(panel)

    def display_error(self, message: str, title: str = "❌ Error"):
        """
        Display an error message in a panel

        Args:
            message: The error message to display
            title: Panel title (default: "❌ Error")
        """
        panel = Panel(
            message,
            title=title,
            border_style="red",
            padding=(1, 2),
        )
        self.error_console.print(panel)

    def display_warning(self, message: str, title: str = "⚠️ Warning"):
        """Display a warning message in a panel"""
        panel = Panel(
            f"[yellow]{message}[/yellow]",
            title=title,
            border_style="yellow",
            padding=(1, 2),
        )
        self.console.print(panel)

    def display_info(self, message: str, title: str = "ℹ️ Info"):
        """Display an info message in a panel"""
        panel = Panel(
            f"[blue]{message}[/blue]",
            title=title,
            border_style="blue",
            padding=(1, 2),
        )
        self.console.print(panel)

    def create_table(self, title: str, columns: list, rows: list) -> Table:
        """
        Create a rich table with the specified columns and rows

        Args:
            title: Table title
            columns: List of column names
            rows: List of row data (each row is a list)

        Returns:
            Table: Configured rich Table object
        """
        table = Table(title=title, show_header=True, header_style="bold magenta")

        # Add columns
        for column in columns:
            table.add_column(column, style="cyan", no_wrap=False)

        # Add rows
        for row in rows:
            table.add_row(*[str(cell) for cell in row])

        return table

    def display_table(self, title: str, columns: list, rows: list):
        """
        Display a table using rich formatting

        Args:
            title: Table title
            columns: List of column names
            rows: List of row data (each row is a list)
        """
        table = self.create_table(title, columns, rows)
        self.console.print(table)

    def prompt_confirmation(self, message: str, default: bool = False) -> bool:
        """
        Prompt user for confirmation

        Args:
            message: The confirmation message
            default: Default value if user just presses enter

        Returns:
            bool: True if confirmed, False otherwise
        """
        default_text = "Y/n" if default else "y/N"
        response = input(f"{message} [{default_text}]: ").lower().strip()

        if not response:
            return default

        return response in ['y', 'yes', '1', 'true']

    def output_data(self, data: Any, format_override: Optional[str] = None):
        """Output data in the specified format (table, json, yaml)"""
        output_format = format_override or self.output_format

        if output_format == 'json':
            from datetime import datetime

            def json_serializer(obj):
                """JSON serializer for datetime objects"""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

            self.console.print(json.dumps(data, indent=2, default=json_serializer))
        elif output_format == 'yaml':
            if yaml is None:
                self.console.print("[yellow]YAML support not available. Install with: pip install pyyaml[/yellow]")
                from datetime import datetime

                def json_serializer(obj):
                    """JSON serializer for datetime objects"""
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

                self.console.print(json.dumps(data, indent=2, default=json_serializer))
            else:
                try:
                    self.console.print(yaml.dump(data, default_flow_style=False))
                except Exception:
                    # Fallback to JSON if YAML fails
                    from datetime import datetime

                    def json_serializer(obj):
                        """JSON serializer for datetime objects"""
                        if isinstance(obj, datetime):
                            return obj.isoformat()
                        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

                    self.console.print(json.dumps(data, indent=2, default=json_serializer))
        else:
            # Default to table format - subclasses should override this
            if isinstance(data, dict):
                self._display_dict_as_table(data)
            elif isinstance(data, list):
                self._display_list_as_table(data)
            else:
                self.console.print(str(data))

    def _display_dict_as_table(self, data: Dict[str, Any]):
        """Display dictionary data as a table"""
        table = Table(title="Data")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        for key, value in data.items():
            table.add_row(str(key), str(value))

        self.console.print(table)

    def _display_list_as_table(self, data: list):
        """Display list data as a table"""
        if not data:
            self.console.print("No data available")
            return

        if isinstance(data[0], dict):
            # Create table from list of dictionaries
            table = Table(title="Data")
            if data:
                for key in data[0].keys():
                    table.add_column(str(key).replace('_', ' ').title())

                for item in data:
                    row = [str(item.get(key, '')) for key in data[0].keys()]
                    table.add_row(*row)

            self.console.print(table)
        else:
            # Simple list
            table = Table(title="Data")
            table.add_column("Item", style="white")

            for item in data:
                table.add_row(str(item))

            self.console.print(table)