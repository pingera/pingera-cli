
"""
Tests for on-demand checks commands
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime

from pingera.models import (
    CheckJob,
    ExecuteCustomCheckRequest,
    ExecuteExistingCheckResponse,
    JobListResponse,
)

from pingera_cli.main import app
from pingera_cli.commands.on_demand_checks import OnDemandChecksCommand


def _execute_response(job_id):
    return ExecuteExistingCheckResponse(job_id=job_id, status="queued", message="Check queued")


@pytest.fixture
def mock_on_demand_api():
    """Mock OnDemandChecksApi returned by OnDemandChecksCommand.get_client"""
    with patch.object(OnDemandChecksCommand, 'get_client') as mock_get_client:
        mock_api = Mock()
        mock_get_client.return_value = mock_api
        yield mock_api


@pytest.fixture
def no_sleep():
    """Make job polling instant"""
    with patch('time.sleep') as mock_sleep:
        yield mock_sleep


class TestOnDemandChecksCommand:
    """Test the OnDemandChecksCommand class"""

    def test_run_custom_web_check(self, cli_runner, mock_on_demand_api, mock_config_with_api_key):
        """Test queueing a custom web check without waiting"""
        mock_on_demand_api.v1_checks_execute_post.return_value = _execute_response("job_123")

        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--url', 'https://example.com',
            '--type', 'web',
            '--name', 'Test On-demand Check',
            '--no-wait',
        ])

        assert result.exit_code == 0
        assert "On-demand check queued successfully" in result.stdout
        assert "Job ID: job_123" in result.stdout
        assert "Type: web" in result.stdout
        assert "URL: https://example.com" in result.stdout

        request = mock_on_demand_api.v1_checks_execute_post.call_args.args[0]
        assert isinstance(request, ExecuteCustomCheckRequest)
        assert request.name == 'Test On-demand Check'
        assert request.type == 'web'
        assert request.url == 'https://example.com'
        mock_on_demand_api.v1_checks_jobs_job_id_get.assert_not_called()

    def test_run_custom_tcp_check(self, cli_runner, mock_on_demand_api, mock_config_with_api_key):
        """Test queueing a custom TCP check without waiting"""
        mock_on_demand_api.v1_checks_execute_post.return_value = _execute_response("tcp_job_456")

        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--host', 'example.com',
            '--port', '80',
            '--type', 'tcp',
            '--name', 'TCP Test',
            '--no-wait',
        ])

        assert result.exit_code == 0
        assert "On-demand check queued successfully" in result.stdout
        assert "Job ID: tcp_job_456" in result.stdout
        assert "Host: example.com" in result.stdout
        assert "Port: 80" in result.stdout

        request = mock_on_demand_api.v1_checks_execute_post.call_args.args[0]
        assert request.type == 'tcp'
        assert request.host == 'example.com'
        assert request.port == 80

    def test_run_custom_synthetic_check_with_script(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, tmp_path):
        """Test running synthetic check with script file"""
        script_file = tmp_path / "test.js"
        script_content = "const { test } = require('@playwright/test'); test('test', async ({ page }) => { await page.goto('https://example.com'); });"
        script_file.write_text(script_content)

        mock_on_demand_api.v1_checks_execute_post.return_value = _execute_response("synthetic_job_789")

        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--type', 'synthetic',
            '--pw-script-file', str(script_file),
            '--name', 'Synthetic Test',
            '--no-wait',
        ])

        assert result.exit_code == 0
        assert "On-demand check queued successfully" in result.stdout
        assert "Job ID: synthetic_job_789" in result.stdout
        # The (long) script path may be wrapped inside the panel, so only check the label
        assert "Script: loaded from" in result.stdout

        request = mock_on_demand_api.v1_checks_execute_post.call_args.args[0]
        assert request.type == 'synthetic'
        assert request.parameters['pw_script'] == script_content

    def test_run_custom_check_validation_errors(self, cli_runner, mock_on_demand_api, mock_config_with_api_key):
        """Test validation errors for custom check execution"""
        # Test web check without URL
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--type', 'web',
            '--name', 'Invalid Web Check'
        ])

        assert result.exit_code == 1
        assert "URL is required for web checks" in result.stderr

        # Test TCP check without host
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--type', 'tcp',
            '--name', 'Invalid TCP Check'
        ])

        assert result.exit_code == 1
        assert "Host is required for tcp checks" in result.stderr
        mock_on_demand_api.v1_checks_execute_post.assert_not_called()

    def test_run_existing_check(self, cli_runner, mock_on_demand_api, mock_config_with_api_key):
        """Test queueing an existing check without waiting"""
        mock_on_demand_api.v1_checks_check_id_execute_post.return_value = _execute_response("existing_job_123")

        result = cli_runner.invoke(app, [
            'checks', 'run', 'existing', 'check_123', '--no-wait'
        ])

        assert result.exit_code == 0
        assert "Existing check executed successfully" in result.stdout
        assert "Job ID: existing_job_123" in result.stdout
        assert "Check ID: check_123" in result.stdout
        mock_on_demand_api.v1_checks_check_id_execute_post.assert_called_once_with(check_id='check_123')

    def test_run_custom_check_json_output(self, cli_runner, mock_on_demand_api, mock_config_with_api_key):
        """Test custom check execution with JSON output"""
        mock_on_demand_api.v1_checks_execute_post.return_value = _execute_response("json_job_123")

        result = cli_runner.invoke(app, [
            '--output', 'json',
            'checks', 'run', 'custom',
            '--url', 'https://example.com',
            '--type', 'web',
            '--no-wait',
        ])

        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert output_data['job_id'] == 'json_job_123'
        assert output_data['check_type'] == 'web'
        assert output_data['url'] == 'https://example.com'
        assert output_data['status'] == 'queued'

    def test_list_jobs_success(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, sample_job_data):
        """Test successful job listing"""
        mock_on_demand_api.v1_checks_jobs_get.return_value = JobListResponse(
            jobs=[CheckJob(**sample_job_data)],
            pagination={'page': 1, 'per_page': 20, 'total': 1, 'pages': 1},
        )

        result = cli_runner.invoke(app, ['--output', 'json', 'checks', 'jobs', 'list'])

        assert result.exit_code == 0
        mock_on_demand_api.v1_checks_jobs_get.assert_called_once_with(page=1, per_page=20)
        output_data = json.loads(result.stdout)
        assert len(output_data['jobs']) == 1
        job = output_data['jobs'][0]
        assert job['job_id'] == 'job_123'
        assert job['name'] == 'Test On-demand Check'
        assert job['type'] == 'web'
        assert job['url'] == 'https://example.com'
        assert job['status'] == 'completed'
        assert output_data['pagination']['total'] == 1

    def test_list_jobs_table_output(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, sample_job_data):
        """Test job listing in table format"""
        mock_on_demand_api.v1_checks_jobs_get.return_value = JobListResponse(
            jobs=[CheckJob(**sample_job_data)],
            pagination={'page': 1, 'per_page': 20, 'total': 1, 'pages': 1},
        )

        result = cli_runner.invoke(app, ['checks', 'jobs', 'list'])

        assert result.exit_code == 0
        assert "Check Jobs" in result.stdout
        assert "job_123" in result.stdout
        assert "web" in result.stdout
        assert "completed" in result.stdout
        assert "1 total items" in result.stdout

    def test_list_jobs_no_results(self, cli_runner, mock_on_demand_api, mock_config_with_api_key):
        """Test job listing with no results"""
        mock_on_demand_api.v1_checks_jobs_get.return_value = JobListResponse(jobs=[])

        result = cli_runner.invoke(app, ['checks', 'jobs', 'list'])

        assert result.exit_code == 0
        assert "No jobs found" in result.stdout

    def test_get_job_status_success(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, sample_job_data):
        """Test job status retrieval (no result_id, so job details are shown)"""
        mock_on_demand_api.v1_checks_jobs_job_id_get.return_value = CheckJob(**sample_job_data)

        result = cli_runner.invoke(app, ['checks', 'jobs', 'status', 'job_123'])

        assert result.exit_code == 0
        mock_on_demand_api.v1_checks_jobs_job_id_get.assert_called_once_with(job_id='job_123')
        assert "Job Status: job_123" in result.stdout
        assert "✅ completed" in result.stdout
        assert "Test On-demand Check" in result.stdout
        assert "Response Time: 120ms" in result.stdout

    def test_get_job_status_json_output(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, sample_job_data):
        """Test job status retrieval with JSON output"""
        mock_on_demand_api.v1_checks_jobs_job_id_get.return_value = CheckJob(**sample_job_data)

        result = cli_runner.invoke(app, [
            '--output', 'json',
            'checks', 'jobs', 'status', 'job_123'
        ])

        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert output_data['job_id'] == 'job_123'
        assert output_data['status'] == 'completed'
        assert output_data['job_type'] == 'on_demand'
        assert output_data['result']['response_time'] == 120

    def test_run_custom_check_with_wait_for_result(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, no_sleep):
        """Test custom check execution waits for the job by default"""
        mock_on_demand_api.v1_checks_execute_post.return_value = _execute_response("wait_job_123")

        job_running = CheckJob(id="wait_job_123", status='running')
        job_completed = CheckJob(
            id="wait_job_123",
            status='completed',
            job_type='on_demand',
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            check_parameters={'name': 'Test Wait Check', 'type': 'web', 'url': 'https://example.com'},
            result={'status': 'ok', 'response_time': 150},
        )

        # Running first, then completed
        mock_on_demand_api.v1_checks_jobs_job_id_get.side_effect = [job_running, job_completed]

        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--url', 'https://example.com',
            '--type', 'web',
            '--name', 'Test Wait Check'
        ])

        assert result.exit_code == 0
        assert mock_on_demand_api.v1_checks_jobs_job_id_get.call_count == 2
        assert "On-demand check queued successfully" in result.stdout
        assert "Job Status: wait_job_123" in result.stdout
        assert "✅ completed" in result.stdout
        assert "Response Time: 150ms" in result.stdout

    def test_run_existing_check_with_wait_for_result(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, no_sleep):
        """Test existing check execution waits for the job by default"""
        mock_on_demand_api.v1_checks_check_id_execute_post.return_value = _execute_response("existing_wait_job")

        mock_on_demand_api.v1_checks_jobs_job_id_get.return_value = CheckJob(
            id="existing_wait_job",
            status='completed',
            job_type='existing_check',
            check_id='check_123',
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            result={'status': 'ok'},
        )

        result = cli_runner.invoke(app, [
            'checks', 'run', 'existing', 'check_123'
        ])

        assert result.exit_code == 0
        mock_on_demand_api.v1_checks_jobs_job_id_get.assert_called_with(job_id='existing_wait_job')
        assert "Job Status: existing_wait_job" in result.stdout
        assert "existing_check" in result.stdout

    def test_wait_for_result_timeout(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, no_sleep):
        """Test waiting gives up with a warning when the job never completes"""
        mock_on_demand_api.v1_checks_execute_post.return_value = _execute_response("timeout_job")
        mock_on_demand_api.v1_checks_jobs_job_id_get.return_value = CheckJob(id="timeout_job", status='running')

        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--url', 'https://example.com',
            '--type', 'web'
        ])

        # The command still succeeds; the job may complete later
        assert result.exit_code == 0
        assert "Job did not complete within 300 seconds" in result.stdout
        # 300s max wait with a 2s poll interval
        assert mock_on_demand_api.v1_checks_jobs_job_id_get.call_count == 150

    def test_wait_for_result_timeout_json_output(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, no_sleep):
        """Test the timeout is reported as JSON in json mode"""
        mock_on_demand_api.v1_checks_execute_post.return_value = _execute_response("timeout_job")
        mock_on_demand_api.v1_checks_jobs_job_id_get.return_value = CheckJob(id="timeout_job", status='running')

        result = cli_runner.invoke(app, [
            '--output', 'json',
            'checks', 'run', 'custom',
            '--url', 'https://example.com',
            '--type', 'web'
        ])

        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert output_data['timeout'] is True
        assert output_data['job_id'] == 'timeout_job'

    def test_on_demand_checks_without_api_key(self, cli_runner, temp_config_dir):
        """Test on-demand checks without API key"""
        # PINGERA_API_KEY is removed by the autouse isolation fixture
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--url', 'https://example.com',
            '--type', 'web'
        ])

        assert result.exit_code == 1
        assert "API key not found" in result.stderr

    def test_invalid_script_file(self, cli_runner, mock_on_demand_api, mock_config_with_api_key):
        """Test synthetic check with non-existent script file"""
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--type', 'synthetic',
            '--pw-script-file', '/nonexistent/file.js',
            '--name', 'Invalid Synthetic'
        ])

        assert result.exit_code == 1
        assert "Playwright script file not found" in result.stderr
        mock_on_demand_api.v1_checks_execute_post.assert_not_called()

    def test_empty_script_file(self, cli_runner, mock_on_demand_api, mock_config_with_api_key, tmp_path):
        """Test synthetic check with empty script file"""
        script_file = tmp_path / "empty.js"
        script_file.write_text("")

        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--type', 'synthetic',
            '--pw-script-file', str(script_file),
            '--name', 'Empty Script'
        ])

        assert result.exit_code == 1
        assert "Playwright script file is empty" in result.stderr
        mock_on_demand_api.v1_checks_execute_post.assert_not_called()
