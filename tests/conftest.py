"""
Pytest configuration and shared fixtures
"""

import pytest
import os
import shutil
import tempfile
import json
from unittest.mock import Mock, patch
from typer.testing import CliRunner
from pathlib import Path

# Importing the CLI instantiates commands that read the config file, so isolate the
# config location before any pingera_cli import (i.e. during test collection too).
_ORIGINAL_ENV = {key: os.environ.get(key) for key in ('XDG_CONFIG_HOME', 'PINGERA_API_KEY')}
_SESSION_XDG_DIR = tempfile.mkdtemp(prefix='pngr-test-xdg-')
os.environ['XDG_CONFIG_HOME'] = _SESSION_XDG_DIR
os.environ.pop('PINGERA_API_KEY', None)


def pytest_unconfigure(config):
    for key, value in _ORIGINAL_ENV.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    shutil.rmtree(_SESSION_XDG_DIR, ignore_errors=True)


from pingera_cli.main import app  # noqa: E402
from pingera_cli.commands.auth import AuthCommand  # noqa: E402
from pingera_cli.utils import config as config_module  # noqa: E402
from pingera_cli.utils.config import get_config_path  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_user_config(tmp_path, monkeypatch):
    """Keep tests away from the real user config and environment."""
    xdg_dir = tmp_path / 'xdg-config'
    xdg_dir.mkdir()
    monkeypatch.setenv('XDG_CONFIG_HOME', str(xdg_dir))
    monkeypatch.delenv('PINGERA_API_KEY', raising=False)
    config_module.set_runtime_overrides()
    yield
    config_module.set_runtime_overrides()


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing"""
    return CliRunner()


@pytest.fixture
def sdk_apis(monkeypatch):
    """
    Patch BaseCommand.api so commands get one Mock per SDK API class.

    Usage: sdk_apis['AlertsApi'].v1_alerts_get.return_value = ...
    """
    from collections import defaultdict
    from pingera_cli.commands.base import BaseCommand

    monkeypatch.setenv('PINGERA_API_KEY', 'test_api_key_1234567890abcdef')
    apis = defaultdict(Mock)
    monkeypatch.setattr(BaseCommand, 'api', lambda self, api_cls: apis[api_cls.__name__])
    return apis


@pytest.fixture
def mock_api_key():
    """Mock API key for testing"""
    return "test_api_key_1234567890abcdef"

@pytest.fixture
def mock_auth_sdk():
    """Mock API key validation for authentication testing only"""
    with patch.object(AuthCommand, '_validate_api_key', return_value="[green]✅ Valid[/green]") as mock_validate:
        yield mock_validate


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory for tests"""
    config_dir = tmp_path / 'pingera-cli'
    config_dir.mkdir(parents=True, exist_ok=True)

    # Patch the config path to use the temporary directory
    with patch('pingera_cli.utils.config.get_config_path') as mock_get_config_path:
        mock_get_config_path.return_value = config_dir / 'config.json'
        yield str(config_dir)


@pytest.fixture
def mock_config_with_api_key(temp_config_dir, mock_api_key):
    """Create a config file with API key for tests"""
    config_file = os.path.join(temp_config_dir, 'config.json')
    config_data = {
        'api_key': mock_api_key,
        'base_url': 'https://api.pingera.ru',
        'output_format': 'table'
    }

    with open(config_file, 'w') as f:
        json.dump(config_data, f)

    # Patch get_config_path to return our test config file as Path object
    with patch('pingera_cli.utils.config.get_config_path') as mock_get_config_path:
        mock_get_config_path.return_value = Path(config_file)
        yield config_file


@pytest.fixture
def mock_pingera_sdk():
    """Mock Pingera SDK"""
    # Mock the actual SDK classes that are used
    with patch('pingera.ApiClient') as mock_api_client, \
         patch('pingera.api.ChecksApi') as mock_checks_api, \
         patch('pingera.api.ChecksUnifiedResultsApi') as mock_unified_api, \
         patch('pingera.Configuration') as mock_config:
        
        # Create mock instances
        mock_client_instance = Mock()
        mock_checks_instance = Mock()
        mock_unified_instance = Mock()
        mock_config_instance = Mock()
        
        # Set up return values
        mock_api_client.return_value = mock_client_instance
        mock_checks_api.return_value = mock_checks_instance
        mock_unified_api.return_value = mock_unified_instance
        mock_config.return_value = mock_config_instance
        
        # Return the checks API instance as the main mock
        yield mock_checks_instance

@pytest.fixture
def mock_pingera_api():
    """Mock Pingera API client - alias for mock_pingera_sdk"""
    # Mock the actual SDK classes that are used
    with patch('pingera.ApiClient') as mock_api_client, \
         patch('pingera.api.ChecksApi') as mock_checks_api, \
         patch('pingera.api.ChecksUnifiedResultsApi') as mock_unified_api, \
         patch('pingera.Configuration') as mock_config:
        
        # Create mock instances
        mock_client_instance = Mock()
        mock_checks_instance = Mock()
        mock_unified_instance = Mock()
        mock_config_instance = Mock()
        
        # Set up return values
        mock_api_client.return_value = mock_client_instance
        mock_checks_api.return_value = mock_checks_instance
        mock_unified_api.return_value = mock_unified_instance
        mock_config.return_value = mock_config_instance
        
        # Return the checks API instance as the main mock
        yield mock_checks_instance


@pytest.fixture
def sample_check_data():
    """Sample check data for testing"""
    return {
        "id": "test_check_123",
        "name": "Test Check",
        "type": "web",
        "url": "https://example.com",
        "status": "ok",
        "active": True,
        "interval": 300,
        "timeout": 30,
        "created_at": "2025-01-01T12:00:00Z",
        "updated_at": "2025-01-01T12:00:00Z",
        "last_checked_at": "2025-01-01T12:05:00Z"
    }


@pytest.fixture
def sample_check_result_data():
    """Sample check result data for testing"""
    return {
        "id": "result_123",
        "check_id": "test_check_123",
        "status": "ok",
        "created_at": "2025-01-01T12:05:00Z",
        "response_time": 150,
        "error_message": None,
        "check_server_id": "server_123",
        "check_metadata": {
            "http_status": 200,
            "response_headers": {"content-type": "text/html"},
            "response_size": 1024
        }
    }


@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return {
        "id": "job_123",
        "status": "completed",
        "job_type": "on_demand",
        "check_id": None,
        "created_at": "2025-01-01T12:00:00Z",
        "started_at": "2025-01-01T12:00:05Z",
        "completed_at": "2025-01-01T12:00:15Z",
        "error_message": None,
        "check_parameters": {
            "name": "Test On-demand Check",
            "type": "web",
            "url": "https://example.com",
            "timeout": 30
        },
        "result": {
            "status": "ok",
            "response_time": 120,
            "check_server": {
                "region": "US",
                "ip_address": "1.2.3.4"
            }
        }
    }