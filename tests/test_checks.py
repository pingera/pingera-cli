
"""
Tests for checks commands
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime
from typer.testing import CliRunner

from pingera_cli.main import app


class TestChecksCommand:
    """Test the ChecksCommand class"""

    def test_list_checks_success(self, cli_runner, mock_config_with_api_key):
        """Test successful checks listing with JSON output"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            # Create mock API client
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            # Mock response
            mock_response = Mock()
            mock_check = Mock()
            mock_check.id = "check_123"
            mock_check.name = "Test Check"
            mock_check.type = "web"
            mock_check.url = "https://example.com"
            mock_check.status = "ok"
            mock_check.interval = 300
            mock_check.created_at = datetime(2023, 1, 1, 12, 0, 0)

            mock_response.checks = [mock_check]
            mock_api.v1_checks_get.return_value = mock_response

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'list'])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert len(output_data['checks']) == 1
            assert output_data['checks'][0]['id'] == 'check_123'
            assert output_data['checks'][0]['name'] == 'Test Check'

    def test_list_checks_no_results(self, cli_runner, mock_config_with_api_key):
        """Test checks listing with no results"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_response = Mock()
            mock_response.checks = []
            mock_api.v1_checks_get.return_value = mock_response

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'list'])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert output_data['checks'] == []
            assert output_data['total'] == 0

    def test_get_check_success(self, cli_runner, mock_config_with_api_key):
        """Test getting specific check details"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_check = Mock()
            mock_check.id = "check_123"
            mock_check.name = "Test Check"
            mock_check.type = "web"
            mock_check.url = "https://example.com"
            mock_check.status = "ok"
            mock_check.active = True
            mock_check.interval = 300
            mock_check.timeout = 30
            mock_check.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_check.updated_at = datetime(2023, 1, 2, 12, 0, 0)
            mock_check.parameters = {"regions": ["US", "EU"]}

            mock_api.v1_checks_check_id_get.return_value = mock_check

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'get', 'check_123'])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert output_data['id'] == 'check_123'
            assert output_data['name'] == 'Test Check'
            assert output_data['active'] is True

    def test_create_web_check_success(self, cli_runner, mock_config_with_api_key):
        """Test creating a web check"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_check = Mock()
            mock_check.id = "new_check_123"
            mock_check.name = "New Web Check"
            mock_check.type = "web"
            mock_check.url = "https://example.com"

            mock_api.v1_checks_post.return_value = mock_check

            result = cli_runner.invoke(app, [
                'checks', 'create',
                '--name', 'New Web Check',
                '--type', 'web',
                '--url', 'https://example.com'
            ])

            assert result.exit_code == 0
            assert "Check 'New Web Check' created successfully" in result.stdout
            assert "ID: new_check_123" in result.stdout

    def test_create_tcp_check_success(self, cli_runner, mock_config_with_api_key):
        """Test creating a TCP check"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_check = Mock()
            mock_check.id = "tcp_check_123"
            mock_check.name = "TCP Check"
            mock_check.type = "tcp"
            mock_check.host = "example.com"
            mock_check.port = 80

            mock_api.v1_checks_post.return_value = mock_check

            result = cli_runner.invoke(app, [
                'checks', 'create',
                '--name', 'TCP Check',
                '--type', 'tcp',
                '--host', 'example.com',
                '--port', '80'
            ])

            assert result.exit_code == 0

    def test_create_check_validation_error(self, cli_runner, mock_config_with_api_key):
        """Test check creation validation errors"""
        result = cli_runner.invoke(app, [
            'checks', 'create',
            '--name', 'Invalid Web Check',
            '--type', 'web'
        ])

        assert result.exit_code == 1
        assert "URL is required for web checks" in result.stderr

    def test_update_check_success(self, cli_runner, mock_config_with_api_key):
        """Test updating a check"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_check = Mock()
            mock_check.id = "check_123"
            mock_check.name = "Updated Check"

            mock_api.v1_checks_check_id_patch.return_value = mock_check

            result = cli_runner.invoke(app, [
                'checks', 'update', 'check_123',
                '--name', 'Updated Check'
            ])

            assert result.exit_code == 0

    def test_delete_check_success(self, cli_runner, mock_config_with_api_key):
        """Test deleting a check with confirmation"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            result = cli_runner.invoke(app, [
                'checks', 'delete', 'check_123', '--confirm'
            ])

            assert result.exit_code == 0
            assert "Check check_123 deleted successfully" in result.stdout
            mock_api.v1_checks_check_id_delete.assert_called_once_with(check_id='check_123')

    def test_get_check_results_success(self, cli_runner, mock_config_with_api_key):
        """Test getting check results"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_unified_results_client') as mock_get_unified_client:
            mock_api = Mock()
            mock_get_unified_client.return_value = mock_api

            mock_response = Mock()
            mock_result = Mock()
            mock_result.id = "result_123"
            mock_result.status = "ok"
            mock_result.response_time = 250
            mock_result.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_result.check_id = "check_123"
            mock_result.check_name = "Test Check"
            mock_result.check_type = "web"

            mock_response.results = [mock_result]
            mock_response.pagination = {"total_items": 1}
            mock_api.v1_checks_all_results_get.return_value = mock_response

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'results', 'check_123'])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert len(output_data['results']) == 1

    def test_get_check_result_detailed_success(self, cli_runner, mock_config_with_api_key):
        """Test getting detailed check result"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_result = Mock()
            mock_result.id = "result_123"
            mock_result.check_id = "check_123"
            mock_result.status = "ok"
            mock_result.response_time = 250
            mock_result.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_result.check_metadata = {"server": "nginx/1.18.0"}

            mock_api.v1_checks_check_id_results_check_result_id_get.return_value = mock_result

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'result', 'check_123', 'result_123'])

            assert result.exit_code == 0

    def test_checks_without_api_key(self, cli_runner, temp_config_dir):
        """Test checks commands without API key"""
        with patch.dict('os.environ', {}, clear=True):
            result = cli_runner.invoke(app, ['checks', 'list'])

        assert result.exit_code == 1
        assert "API key not found" in result.stderr

    def test_create_synthetic_check_with_script_file(self, cli_runner, mock_config_with_api_key, tmp_path):
        """Test creating synthetic check with script file"""
        script_file = tmp_path / "test_script.js"
        script_file.write_text("const { test } = require('@playwright/test'); test('example', async ({ page }) => { await page.goto('https://example.com'); });")

        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_check = Mock()
            mock_check.id = "synthetic_check_123"
            mock_check.name = "Synthetic Check"
            mock_check.type = "synthetic"

            mock_api.v1_checks_post.return_value = mock_check

            result = cli_runner.invoke(app, [
                'checks', 'create',
                '--name', 'Synthetic Check',
                '--type', 'synthetic',
                '--pw-script-file', str(script_file)
            ])

            assert result.exit_code == 0

    def test_create_check_with_parameters(self, cli_runner, mock_config_with_api_key):
        """Test creating check with JSON parameters"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_check = Mock()
            mock_check.id = "param_check_123"
            mock_check.name = "Parameterized Check"

            mock_api.v1_checks_post.return_value = mock_check

            result = cli_runner.invoke(app, [
                'checks', 'create',
                '--name', 'Parameterized Check',
                '--type', 'web',
                '--url', 'https://example.com',
                '--parameters', '{"regions": ["US", "EU"]}'
            ])

            assert result.exit_code == 0

    def test_invalid_parameters_json(self, cli_runner, mock_config_with_api_key):
        """Test creating check with invalid JSON parameters"""
        result = cli_runner.invoke(app, [
            'checks', 'create',
            '--name', 'Invalid Check',
            '--type', 'web',
            '--url', 'https://example.com',
            '--parameters', 'invalid json'
        ])

        assert result.exit_code == 1
        assert "Invalid JSON in --parameters" in result.stderr

    def test_list_regions_success(self, cli_runner, mock_config_with_api_key):
        """Test listing regions successfully"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            # Mock response with actual SDK attributes
            mock_response = Mock()
            mock_region = Mock()
            mock_region.id = "US, East coast"
            mock_region.display_name = "US, East, South Carolina"
            mock_region.available_check_types = ["web", "api", "tcp", "ssl", "synthetic", "multistep"]

            mock_response.regions = [mock_region]
            mock_api.v1_checks_get_regions_get.return_value = mock_response

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'list-regions'])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert len(output_data['regions']) == 1
            assert output_data['regions'][0]['id'] == 'US, East coast'
            assert output_data['regions'][0]['display_name'] == 'US, East, South Carolina'

    def test_list_regions_with_filter(self, cli_runner, mock_config_with_api_key):
        """Test listing regions with check type filter"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_response = Mock()
            mock_region = Mock()
            mock_region.id = "EU, West"
            mock_region.display_name = "Europe, West, Belgium"
            mock_region.available_check_types = ["synthetic", "multistep"]

            mock_response.regions = [mock_region]
            mock_api.v1_checks_get_regions_get.return_value = mock_response

            result = cli_runner.invoke(app, [
                '--output', 'json', 'checks', 'list-regions', '--type', 'synthetic'
            ])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert output_data['filter']['check_type'] == 'synthetic'
            mock_api.v1_checks_get_regions_get.assert_called_with(check_type='synthetic')

    def test_list_regions_no_results(self, cli_runner, mock_config_with_api_key):
        """Test listing regions with no results"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_response = Mock()
            mock_response.regions = []
            mock_api.v1_checks_get_regions_get.return_value = mock_response

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'list-regions'])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert output_data['regions'] == []
            assert output_data['total'] == 0
