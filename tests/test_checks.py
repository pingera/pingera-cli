
"""
Tests for checks commands
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime
from typer.testing import CliRunner
from pingera.models import (
    MonitorCheck,
    MonitorCheckList,
    Region,
    RegionsList,
    UnifiedResult,
    UnifiedResultList,
)

from pingera_cli.main import app


class TestChecksCommand:
    """Test the ChecksCommand class"""

    def test_list_checks_success(self, cli_runner, mock_config_with_api_key):
        """Test successful checks listing with JSON output"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            # Create mock API client
            mock_api = Mock()
            mock_get_client.return_value = mock_api

            mock_check = MonitorCheck(
                id="check_123",
                name="Test Check",
                type="web",
                url="https://example.com",
                status="ok",
                interval=300,
                created_at=datetime(2023, 1, 1, 12, 0, 0),
            )
            mock_api.v1_checks_get.return_value = MonitorCheckList(checks=[mock_check])

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'list'])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert len(output_data['checks']) == 1
            assert output_data['checks'][0]['id'] == 'check_123'
            assert output_data['checks'][0]['name'] == 'Test Check'
            assert output_data['checks'][0]['interval'] == 300
            assert output_data['checks'][0]['created_at'] == '2023-01-01T12:00:00'
            assert output_data['total'] == 1

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

            mock_check = MonitorCheck(
                id="check_123",
                name="Test Check",
                type="web",
                url="https://example.com",
                status="ok",
                active=True,
                interval=300,
                timeout=30,
                created_at=datetime(2023, 1, 1, 12, 0, 0),
                updated_at=datetime(2023, 1, 2, 12, 0, 0),
                parameters={"regions": ["US", "EU"]},
            )

            mock_api.v1_checks_check_id_get.return_value = mock_check

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'get', 'check_123'])

            assert result.exit_code == 0
            mock_api.v1_checks_check_id_get.assert_called_once_with(check_id='check_123')
            output_data = json.loads(result.stdout)
            assert output_data['id'] == 'check_123'
            assert output_data['name'] == 'Test Check'
            assert output_data['active'] is True
            assert output_data['parameters'] == {"regions": ["US", "EU"]}

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

            mock_result = UnifiedResult(
                id="result_123",
                status="ok",
                response_time=250,
                created_at=datetime(2023, 1, 1, 12, 0, 0),
                check_id="check_123",
                check_name="Test Check",
                check_type="web",
            )
            mock_api.v1_checks_all_results_get.return_value = UnifiedResultList(
                results=[mock_result], pagination={"total_items": 1}
            )

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'results', 'check_123'])

            assert result.exit_code == 0
            mock_api.v1_checks_all_results_get.assert_called_once_with(page=1, page_size=20, check_id='check_123')
            output_data = json.loads(result.stdout)
            assert len(output_data['results']) == 1
            assert output_data['results'][0]['id'] == 'result_123'
            assert output_data['results'][0]['response_time'] == 250
            assert output_data['pagination']['total_items'] == 1

    def test_get_check_result_detailed_success(self, cli_runner, mock_config_with_api_key):
        """Test getting detailed check result"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_unified_results_client') as mock_get_unified_client:
            mock_api = Mock()
            mock_get_unified_client.return_value = mock_api

            mock_result = UnifiedResult(
                id="result_123",
                check_id="check_123",
                status="ok",
                response_time=250,
                created_at=datetime(2023, 1, 1, 12, 0, 0),
                check_metadata={"server": "nginx/1.18.0"},
            )
            mock_api.v1_checks_all_results_get.return_value = UnifiedResultList(results=[mock_result])

            result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'result', 'result_123'])

            assert result.exit_code == 0
            mock_api.v1_checks_all_results_get.assert_called_once_with(result_id='result_123')
            output_data = json.loads(result.stdout)
            assert output_data['id'] == 'result_123'
            assert output_data['check_id'] == 'check_123'
            assert output_data['check_metadata'] == {"server": "nginx/1.18.0"}

    def test_get_check_result_detailed_not_found(self, cli_runner, mock_config_with_api_key):
        """Test detailed result lookup for an unknown result ID"""
        with patch('pingera_cli.commands.checks.ChecksCommand.get_unified_results_client') as mock_get_unified_client:
            mock_api = Mock()
            mock_get_unified_client.return_value = mock_api
            mock_api.v1_checks_all_results_get.return_value = UnifiedResultList(results=[])

            result = cli_runner.invoke(app, ['checks', 'result', 'missing_result'])

            assert result.exit_code == 1
            assert "Result missing_result not found" in result.stderr

    def test_checks_without_api_key(self, cli_runner, temp_config_dir):
        """Test checks commands without API key"""
        # PINGERA_API_KEY is removed by the autouse isolation fixture
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

            mock_region = Region(
                id="US, East coast",
                display_name="US, East, South Carolina",
                available_check_types=["web", "api", "tcp", "ssl", "synthetic", "multistep"],
            )
            mock_api.v1_checks_get_regions_get.return_value = RegionsList(regions=[mock_region])

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

            mock_region = Region(
                id="EU, West",
                display_name="Europe, West, Belgium",
                available_check_types=["synthetic", "multistep"],
            )
            mock_api.v1_checks_get_regions_get.return_value = RegionsList(regions=[mock_region])

            result = cli_runner.invoke(app, [
                '--output', 'json', 'checks', 'list-regions', '--type', 'synthetic'
            ])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert output_data['filter']['check_type'] == 'synthetic'
            assert output_data['regions'][0]['available_check_types'] == ["synthetic", "multistep"]
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


class TestCheckScheduling:
    """Cron scheduling and machine-readable output of create/update"""

    def _created(self, **overrides):
        data = dict(id="chk_1", name="n", type="web", url="https://example.com", status="pending",
                    created_at=datetime(2026, 1, 1, 12, 0, 0))
        data.update(overrides)
        return MonitorCheck(**data)

    def test_create_with_cron_json_includes_read_only_fields(self, cli_runner, mock_config_with_api_key):
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            api = mock_get_client.return_value
            api.v1_checks_post.return_value = self._created(scheduling_type="cron", cron_schedule="0 9 * * 1-5")

            result = cli_runner.invoke(app, ['-o', 'json', 'checks', 'create', '--name', 'n', '--type', 'web',
                                             '--url', 'https://example.com', '--cron', '0 9 * * 1-5'])

            assert result.exit_code == 0, result.output
            body = api.v1_checks_post.call_args.kwargs['monitor_check']
            assert body['scheduling_type'] == 'cron'
            assert body['cron_schedule'] == '0 9 * * 1-5'
            assert 'interval' not in body
            data = json.loads(result.stdout)
            assert data['id'] == 'chk_1'
            assert data['status'] == 'pending'
            assert data['cron_schedule'] == '0 9 * * 1-5'

    def test_create_defaults_to_interval(self, cli_runner, mock_config_with_api_key):
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            api = mock_get_client.return_value
            api.v1_checks_post.return_value = self._created(interval=300)

            result = cli_runner.invoke(app, ['checks', 'create', '--name', 'n', '--url', 'https://example.com'])

            assert result.exit_code == 0, result.output
            body = api.v1_checks_post.call_args.kwargs['monitor_check']
            assert body['scheduling_type'] == 'interval'
            assert body['interval'] == 300
            assert "every 300s" in result.stdout

    def test_interval_and_cron_conflict(self, cli_runner, mock_config_with_api_key):
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            result = cli_runner.invoke(app, ['checks', 'create', '--name', 'n', '--url', 'https://example.com',
                                             '--interval', '60', '--cron', '* * * * *'])
            assert result.exit_code == 1
            assert "either --interval or --cron" in result.stderr
            mock_get_client.return_value.v1_checks_post.assert_not_called()

    def test_update_switches_to_cron(self, cli_runner, mock_config_with_api_key):
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            api = mock_get_client.return_value
            api.v1_checks_check_id_patch.return_value = self._created(scheduling_type="cron", cron_schedule="*/5 * * * *")

            result = cli_runner.invoke(app, ['checks', 'update', 'chk_1', '--cron', '*/5 * * * *'])

            assert result.exit_code == 0, result.output
            api.v1_checks_check_id_patch.assert_called_once_with(
                check_id='chk_1', monitor_check1={'scheduling_type': 'cron', 'cron_schedule': '*/5 * * * *'}
            )
            assert "cron '*/5 * * * *'" in result.stdout

    def test_get_cron_check_without_interval(self, cli_runner, mock_config_with_api_key):
        with patch('pingera_cli.commands.checks.ChecksCommand.get_client') as mock_get_client:
            mock_get_client.return_value.v1_checks_check_id_get.return_value = self._created(
                scheduling_type="cron", cron_schedule="0 0 * * *", active=True, timeout=30
            )
            result = cli_runner.invoke(app, ['checks', 'get', 'chk_1'])
            assert result.exit_code == 0, result.output
            assert "cron '0 0 * * *'" in result.stdout
