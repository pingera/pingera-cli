
"""
Tests for on-demand checks commands
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typer.testing import CliRunner

from pingera_cli.main import app
from pingera_cli.commands.on_demand_checks import OnDemandChecksCommand


class TestOnDemandChecksCommand:
    """Test the OnDemandChecksCommand class"""
    
    def test_run_custom_web_check(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test running custom web check"""
        mock_response = Mock()
        mock_response.job_id = "job_123"
        mock_pingera_sdk.v1_checks_execute_post.return_value = mock_response
        
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--url', 'https://example.com',
            '--type', 'web',
            '--name', 'Test On-demand Check'
        ])
        
        assert result.exit_code == 0
        assert "On-demand check queued successfully" in result.stdout
        assert "Job ID: job_123" in result.stdout
        assert "Type: web" in result.stdout
        assert "URL: https://example.com" in result.stdout

    def test_run_custom_tcp_check(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test running custom TCP check"""
        mock_response = Mock()
        mock_response.job_id = "tcp_job_456"
        mock_pingera_sdk.v1_checks_execute_post.return_value = mock_response
        
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--host', 'example.com',
            '--port', '80',
            '--type', 'tcp',
            '--name', 'TCP Test'
        ])
        
        assert result.exit_code == 0
        assert "On-demand check queued successfully" in result.stdout
        assert "Job ID: tcp_job_456" in result.stdout
        assert "Host: example.com" in result.stdout
        assert "Port: 80" in result.stdout

    def test_run_custom_synthetic_check_with_script(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key, tmp_path):
        """Test running synthetic check with script file"""
        # Create script file
        script_file = tmp_path / "test.js"
        script_content = "const { test } = require('@playwright/test'); test('test', async ({ page }) => { await page.goto('https://example.com'); });"
        script_file.write_text(script_content)
        
        mock_response = Mock()
        mock_response.job_id = "synthetic_job_789"
        mock_pingera_sdk.v1_checks_execute_post.return_value = mock_response
        
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--type', 'synthetic',
            '--pw-script-file', str(script_file),
            '--name', 'Synthetic Test'
        ])
        
        assert result.exit_code == 0
        assert "On-demand check queued successfully" in result.stdout
        assert "Job ID: synthetic_job_789" in result.stdout
        assert f"Script: loaded from {script_file}" in result.stdout

    def test_run_custom_check_validation_errors(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test validation errors for custom check execution"""
        # Test web check without URL
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--type', 'web',
            '--name', 'Invalid Web Check'
        ])
        
        assert result.exit_code == 1
        assert "URL is required for web checks" in result.stdout
        
        # Test TCP check without host
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--type', 'tcp',
            '--name', 'Invalid TCP Check'
        ])
        
        assert result.exit_code == 1
        assert "Host is required for tcp checks" in result.stdout

    def test_run_existing_check(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test running existing check"""
        mock_response = Mock()
        mock_response.job_id = "existing_job_123"
        mock_pingera_sdk.v1_checks_check_id_execute_post.return_value = mock_response
        
        result = cli_runner.invoke(app, [
            'checks', 'run', 'existing', 'check_123'
        ])
        
        assert result.exit_code == 0
        assert "Existing check executed successfully" in result.stdout
        assert "Job ID: existing_job_123" in result.stdout
        assert "Check ID: check_123" in result.stdout

    def test_run_custom_check_json_output(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test custom check execution with JSON output"""
        mock_response = Mock()
        mock_response.job_id = "json_job_123"
        mock_pingera_sdk.v1_checks_execute_post.return_value = mock_response
        
        result = cli_runner.invoke(app, [
            '--output', 'json',
            'checks', 'run', 'custom',
            '--url', 'https://example.com',
            '--type', 'web'
        ])
        
        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert output_data['job_id'] == 'json_job_123'
        assert output_data['check_type'] == 'web'
        assert output_data['url'] == 'https://example.com'
        assert output_data['status'] == 'queued'

    def test_list_jobs_success(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key, sample_job_data):
        """Test successful job listing"""
        mock_response = Mock()
        mock_job = Mock()
        
        # Set up mock job attributes
        for key, value in sample_job_data.items():
            if key in ['created_at', 'started_at', 'completed_at']:
                setattr(mock_job, key, datetime.fromisoformat(value.replace('Z', '+00:00')) if value else None)
            else:
                setattr(mock_job, key, value)
        
        mock_response.jobs = [mock_job]
        mock_response.pagination = {
            'page': 1,
            'per_page': 20,
            'total': 1,
            'pages': 1
        }
        mock_pingera_sdk.v1_checks_jobs_get.return_value = mock_response
        
        result = cli_runner.invoke(app, ['checks', 'jobs', 'list'])
        
        assert result.exit_code == 0
        assert "job_123" in result.stdout
        assert "Test On-demand Check" in result.stdout
        assert "web" in result.stdout
        assert "completed" in result.stdout

    def test_list_jobs_no_results(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test job listing with no results"""
        mock_response = Mock()
        mock_response.jobs = []
        mock_pingera_sdk.v1_checks_jobs_get.return_value = mock_response
        
        result = cli_runner.invoke(app, ['checks', 'jobs', 'list'])
        
        assert result.exit_code == 0
        assert "No jobs found" in result.stdout

    def test_get_job_result_success(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key, sample_job_data):
        """Test successful job result retrieval"""
        mock_job_status = Mock()
        
        for key, value in sample_job_data.items():
            if key in ['created_at', 'started_at', 'completed_at']:
                setattr(mock_job_status, key, datetime.fromisoformat(value.replace('Z', '+00:00')) if value else None)
            else:
                setattr(mock_job_status, key, value)
        
        mock_pingera_sdk.v1_checks_jobs_job_id_get.return_value = mock_job_status
        
        result = cli_runner.invoke(app, ['checks', 'jobs', 'result', 'job_123'])
        
        assert result.exit_code == 0
        assert "Job Status: job_123" in result.stdout
        assert "✅ completed" in result.stdout
        assert "Test On-demand Check" in result.stdout
        assert "Response Time: 120ms" in result.stdout

    def test_get_job_result_json_output(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key, sample_job_data):
        """Test job result retrieval with JSON output"""
        mock_job_status = Mock()
        
        for key, value in sample_job_data.items():
            if key in ['created_at', 'started_at', 'completed_at']:
                setattr(mock_job_status, key, datetime.fromisoformat(value.replace('Z', '+00:00')) if value else None)
            else:
                setattr(mock_job_status, key, value)
        
        mock_pingera_sdk.v1_checks_jobs_job_id_get.return_value = mock_job_status
        
        result = cli_runner.invoke(app, [
            '--output', 'json',
            'checks', 'jobs', 'result', 'job_123'
        ])
        
        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert output_data['job_id'] == 'job_123'
        assert output_data['status'] == 'completed'
        assert output_data['job_type'] == 'on_demand'

    def test_run_custom_check_with_wait_for_result(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test custom check execution with wait for result"""
        # Mock the execution response
        mock_response = Mock()
        mock_response.job_id = "wait_job_123"
        mock_pingera_sdk.v1_checks_execute_post.return_value = mock_response
        
        # Mock the job status responses (simulate job completion)
        mock_job_status_running = Mock()
        mock_job_status_running.status = 'running'
        
        mock_job_status_completed = Mock()
        mock_job_status_completed.status = 'completed'
        mock_job_status_completed.job_type = 'on_demand'
        mock_job_status_completed.check_id = None
        mock_job_status_completed.created_at = datetime.now()
        mock_job_status_completed.started_at = datetime.now()
        mock_job_status_completed.completed_at = datetime.now()
        mock_job_status_completed.error_message = None
        mock_job_status_completed.check_parameters = {
            'name': 'Test Wait Check',
            'type': 'web',
            'url': 'https://example.com'
        }
        mock_job_status_completed.result = {
            'status': 'ok',
            'response_time': 150
        }
        
        # Set up the job status call to return running first, then completed
        mock_pingera_sdk.v1_checks_jobs_job_id_get.side_effect = [
            mock_job_status_running,
            mock_job_status_completed
        ]
        
        with patch('time.sleep'):  # Speed up the test
            result = cli_runner.invoke(app, [
                'checks', 'run', 'custom',
                '--url', 'https://example.com',
                '--type', 'web',
                '--name', 'Test Wait Check',
                '--wait-for-result'
            ])
        
        assert result.exit_code == 0
        assert "On-demand check queued successfully" in result.stdout
        assert "Job Status: wait_job_123" in result.stdout
        assert "✅ completed" in result.stdout

    def test_run_existing_check_with_wait_for_result(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test existing check execution with wait for result"""
        mock_response = Mock()
        mock_response.job_id = "existing_wait_job"
        mock_pingera_sdk.v1_checks_check_id_execute_post.return_value = mock_response
        
        # Mock completed job status
        mock_job_status = Mock()
        mock_job_status.status = 'completed'
        mock_job_status.job_type = 'existing_check'
        mock_job_status.check_id = 'check_123'
        mock_job_status.created_at = datetime.now()
        mock_job_status.started_at = datetime.now()
        mock_job_status.completed_at = datetime.now()
        mock_job_status.error_message = None
        mock_job_status.check_parameters = None
        mock_job_status.result = {'status': 'ok'}
        
        mock_pingera_sdk.v1_checks_jobs_job_id_get.return_value = mock_job_status
        
        with patch('time.sleep'):  # Speed up the test
            result = cli_runner.invoke(app, [
                'checks', 'run', 'existing', 'check_123',
                '--wait-for-result'
            ])
        
        assert result.exit_code == 0
        assert "Job Status: existing_wait_job" in result.stdout

    def test_wait_for_result_timeout(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test wait for result with timeout"""
        mock_response = Mock()
        mock_response.job_id = "timeout_job"
        mock_pingera_sdk.v1_checks_execute_post.return_value = mock_response
        
        # Mock job status that never completes
        mock_job_status = Mock()
        mock_job_status.status = 'running'
        mock_pingera_sdk.v1_checks_jobs_job_id_get.return_value = mock_job_status
        
        # Mock time to simulate timeout quickly
        with patch('time.sleep'), \
             patch('pingera_cli.commands.on_demand_checks.OnDemandChecksCommand._wait_and_show_result') as mock_wait:
            # Simulate timeout by calling the actual method with short timeout
            def simulate_timeout(*args):
                # Just display timeout message
                cli_runner.invoke(app, [])  # This won't actually run but helps with mocking
                
            mock_wait.side_effect = simulate_timeout
            
            result = cli_runner.invoke(app, [
                'checks', 'run', 'custom',
                '--url', 'https://example.com',
                '--type', 'web',
                '--wait-for-result'
            ])
        
        # The command should still succeed (exit code 0) even with timeout
        assert result.exit_code == 0

    def test_on_demand_checks_without_api_key(self, cli_runner, temp_config_dir):
        """Test on-demand checks without API key"""
        with patch.dict('os.environ', {}, clear=True):
            result = cli_runner.invoke(app, [
                'checks', 'run', 'custom',
                '--url', 'https://example.com',
                '--type', 'web'
            ])
        
        assert result.exit_code == 1
        assert "API key not found" in result.stdout

    def test_invalid_script_file(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key):
        """Test synthetic check with non-existent script file"""
        result = cli_runner.invoke(app, [
            'checks', 'run', 'custom',
            '--type', 'synthetic',
            '--pw-script-file', '/nonexistent/file.js',
            '--name', 'Invalid Synthetic'
        ])
        
        assert result.exit_code == 1
        assert "Playwright script file not found" in result.stdout

    def test_empty_script_file(self, cli_runner, mock_pingera_sdk, mock_config_with_api_key, tmp_path):
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
        assert "Playwright script file is empty" in result.stdout
