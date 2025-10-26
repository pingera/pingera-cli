"""
Configuration management utilities
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

from .console import console, error_console


def get_config_path() -> Path:
    """
    Get the path to the configuration file

    Returns:
        Path: Path to the config file
    """
    # Use XDG_CONFIG_HOME if available, otherwise use ~/.config
    config_dir = os.getenv('XDG_CONFIG_HOME')
    if config_dir:
        config_path = Path(config_dir) / 'pingera-cli'
    else:
        config_path = Path.home() / '.config' / 'pingera-cli'

    try:
        config_path.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        # If we can't create the directory, use a temp location for tests
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / 'pingera-cli'
        temp_dir.mkdir(parents=True, exist_ok=True)
        config_path = temp_dir

    return config_path / 'config.json'


def get_config() -> Dict[str, Any]:
    """
    Load configuration from file or return default configuration

    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    default_config = {
        'base_url': 'https://api.pingera.ru',
        'output_format': 'table',
        'verbose': False,
        'color': True,
        'timeout': 30.0,
        'retries': 3,
        'config_path': str(get_config_path()),
    }

    config_path = get_config_path()

    if not config_path.exists():
        return default_config

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Merge with defaults to ensure all keys are present
        merged_config = default_config.copy()
        merged_config.update(config)
        return merged_config

    except (json.JSONDecodeError, IOError) as e:
        error_console.print(f"[danger]Error reading config file: {e}[/danger]")
        return default_config


def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to file

    Args:
        config: Configuration dictionary to save

    Returns:
        bool: True if saved successfully, False otherwise
    """
    config_path = get_config_path()

    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True

    except IOError as e:
        error_console.print(f"[danger]Error saving config file: {e}[/danger]")
        return False


def get_api_key() -> Optional[str]:
    """
    Get API key from environment or config

    Returns:
        Optional[str]: API key if found, None otherwise
    """
    # First try environment variable
    api_key = os.getenv('PINGERA_API_KEY')
    if api_key:
        return api_key

    # Then try config file
    config = get_config()
    return config.get('api_key')


def set_api_key(api_key: str) -> bool:
    """
    Set API key in configuration file

    Args:
        api_key: API key to save

    Returns:
        bool: True if saved successfully, False otherwise
    """
    if not api_key or not api_key.strip():
        return False

    config = get_config()
    config['api_key'] = api_key.strip()
    return save_config(config)


def set_output_format(output_format: str) -> bool:
    """
    Set output format in configuration file

    Args:
        output_format: Output format (table, json, yaml)

    Returns:
        bool: True if saved successfully, False otherwise
    """
    if output_format not in ['table', 'json', 'yaml']:
        return False

    config = get_config()
    config['output_format'] = output_format
    return save_config(config)


def get_output_format() -> str:
    """
    Get output format from configuration

    Returns:
        str: Output format (default: table)
    """
    config = get_config()
    return config.get('output_format', 'table')


def validate_config() -> Dict[str, bool]:
    """
    Validate current configuration

    Returns:
        Dict[str, bool]: Validation results
    """
    results = {
        'api_key_set': bool(get_api_key()),
        'config_file_exists': get_config_path().exists(),
        'config_file_readable': True,
        'pingera_sdk_available': True,
    }

    # Test config file readability
    try:
        get_config()
    except Exception:
        results['config_file_readable'] = False

    # Test Pingera SDK availability
    try:
        from pingera import ApiClient
    except ImportError:
        results['pingera_sdk_available'] = False

    return results