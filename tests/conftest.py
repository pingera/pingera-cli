"""
Pytest configuration and shared fixtures
"""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, patch
from typer.testing import CliRunner
from pathlib import Path

from pingera_cli.main import app
from pingera_cli.utils.config import get_config_path


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing"""
    return CliRunner()


@pytest.fixture
def mock_api_key():
    """Mock API key for testing"""
    return "test_api_key_1234567890abcdef"

@pytest.fixture
def mock_auth_sdk():
    """Mock SDK for authentication testing only"""
    with patch('pingera_cli.commands.auth.validate_api_key') as mock_validate:
        mock_validate.return_value = True
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