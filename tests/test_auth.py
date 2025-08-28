"""
Tests for authentication commands
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, call
from typer.testing import CliRunner

from pingera_cli.main import app
from pingera_cli.commands.auth import AuthCommand


class TestAuthCommand:
    """Test the AuthCommand class"""

    def test_login_with_api_key(self, temp_config_dir, mock_api_key):
        """Test login with API key provided"""
        runner = CliRunner()

        with patch.dict(os.environ, {}, clear=True):
            with patch('pingera_cli.utils.config.set_api_key', return_value=True):
                result = runner.invoke(app, ['auth', 'login', '--api-key', mock_api_key])

        assert result.exit_code == 0
        assert "API key has been saved successfully" in result.stdout
        assert "Authentication Success" in result.stdout

        # Check that config file was created with API key
        config_file = os.path.join(temp_config_dir, 'config.json')
        assert os.path.exists(config_file)

        with open(config_file, 'r') as f:
            config_data = json.load(f)
            assert config_data['api_key'] == mock_api_key

    def test_login_interactive_mode(self, temp_config_dir, mock_api_key):
        """Test interactive login mode"""
        runner = CliRunner()

        with patch('pingera_cli.commands.auth.Prompt.ask', return_value=mock_api_key):
            with patch('pingera_cli.utils.config.set_api_key', return_value=True):
                result = runner.invoke(app, ['auth', 'login', '--interactive'])

        assert result.exit_code == 0
        assert "API key has been saved successfully" in result.stdout

    def test_login_empty_api_key_interactive_fallback(self, temp_config_dir, mock_api_key):
        """Test login with empty API key falls back to interactive mode"""
        runner = CliRunner()

        with patch('pingera_cli.commands.auth.Prompt.ask', return_value=mock_api_key):
            with patch('pingera_cli.utils.config.set_api_key', return_value=True):
                result = runner.invoke(app, ['auth', 'login', '--api-key', ''])

        assert result.exit_code == 0
        assert "API key has been saved successfully" in result.stdout

    def test_login_whitespace_api_key_interactive_fallback(self, temp_config_dir, mock_api_key):
        """Test login with whitespace-only API key falls back to interactive mode"""
        runner = CliRunner()

        with patch('pingera_cli.commands.auth.Prompt.ask', return_value=mock_api_key):
            with patch('pingera_cli.utils.config.set_api_key', return_value=True):
                result = runner.invoke(app, ['auth', 'login', '--api-key', '   '])

        assert result.exit_code == 0
        assert "API key has been saved successfully" in result.stdout

    def test_login_interactive_empty_input(self, temp_config_dir):
        """Test interactive login with empty input"""
        runner = CliRunner()

        with patch('pingera_cli.commands.auth.Prompt.ask', return_value=''):
            result = runner.invoke(app, ['auth', 'login', '--interactive'])

        assert result.exit_code == 1
        assert "API key cannot be empty" in result.stdout

    def test_login_short_api_key(self, temp_config_dir):
        """Test login with suspiciously short API key"""
        runner = CliRunner()
        short_key = "123"

        with patch('pingera_cli.utils.config.set_api_key', return_value=True):
            result = runner.invoke(app, ['auth', 'login', '--api-key', short_key])

        assert result.exit_code == 0  # Should still succeed but with warning
        assert "API key seems too short" in result.stdout

    def test_status_with_api_key(self, mock_config_with_api_key, mock_api_key):
        """Test status command when API key is configured"""
        runner = CliRunner()

        with patch.dict(os.environ, {'PINGERA_API_KEY': mock_api_key}):
            with patch('pingera_cli.utils.config.get_api_key', return_value=mock_api_key):
                result = runner.invoke(app, ['auth', 'status'])

        assert result.exit_code == 0
        assert "Authentication Status" in result.stdout
        assert "API Key: ✓ Set" in result.stdout

    def test_status_with_env_api_key(self, temp_config_dir, mock_api_key):
        """Test status command with API key in environment variable"""
        runner = CliRunner()

        with patch.dict(os.environ, {'PINGERA_API_KEY': mock_api_key}):
            with patch('pingera_cli.utils.config.get_api_key', return_value=mock_api_key):
                result = runner.invoke(app, ['auth', 'status'])

        assert result.exit_code == 0
        assert "✅ Authenticated" in result.stdout
        assert "environment variable" in result.stdout

    def test_status_without_api_key(self, temp_config_dir):
        """Test status command when no API key is configured"""
        runner = CliRunner()

        with patch.dict(os.environ, {}, clear=True):
            with patch('pingera_cli.utils.config.get_api_key', return_value=None):
                result = runner.invoke(app, ['auth', 'status'])

        assert result.exit_code == 0
        assert "Authentication Status" in result.stdout
        assert "API Key: ✗ Not set" in result.stdout

    def test_logout_with_confirm(self, mock_config_with_api_key):
        """Test logout with confirmation"""
        runner = CliRunner()

        with patch.dict(os.environ, {}, clear=True):
            with patch('pingera_cli.utils.config.get_config', return_value={'api_key': 'test_key'}):
                with patch('pingera_cli.utils.config.save_config', return_value=True):
                    result = runner.invoke(app, ['auth', 'logout', '--confirm'])

        assert result.exit_code == 0
        assert "Credentials cleared from configuration file" in result.stdout

    def test_logout_no_credentials(self, temp_config_dir):
        """Test logout when no credentials exist"""
        runner = CliRunner()

        with patch.dict(os.environ, {}, clear=True):
            with patch('pingera_cli.utils.config.get_config', return_value={}):
                with patch('pingera_cli.utils.config.save_config', return_value=True):
                    result = runner.invoke(app, ['auth', 'logout', '--confirm'])

        assert result.exit_code == 0
        assert "No stored credentials found" in result.stdout

    def test_logout_with_env_variable(self, mock_config_with_api_key, mock_api_key):
        """Test logout warning when API key is in environment"""
        runner = CliRunner()

        with patch.dict(os.environ, {'PINGERA_API_KEY': mock_api_key}):
            with patch('pingera_cli.utils.config.get_config', return_value={'api_key': 'test_key'}):
                with patch('pingera_cli.utils.config.save_config', return_value=True):
                    result = runner.invoke(app, ['auth', 'logout', '--confirm'])

        assert result.exit_code == 0
        assert "Environment variable PINGERA_API_KEY is still set" in result.stdout

    def test_logout_interactive_cancel(self, mock_config_with_api_key):
        """Test logout cancellation in interactive mode"""
        runner = CliRunner()

        with patch('pingera_cli.commands.base.BaseCommand.prompt_confirmation', return_value=False):
            result = runner.invoke(app, ['auth', 'logout'])

        assert result.exit_code == 0
        assert "Logout cancelled" in result.stdout

    def test_auth_command_initialization(self):
        """Test AuthCommand initialization"""
        auth_cmd = AuthCommand()

        assert auth_cmd.app is not None
        assert auth_cmd.app.info.name == "auth"
        assert "authentication settings" in auth_cmd.app.info.help.lower()

    @patch('pingera_cli.utils.config.save_config')
    def test_login_config_save_failure(self, mock_save_config, temp_config_dir, mock_api_key):
        """Test login when config save fails"""
        mock_save_config.return_value = False
        runner = CliRunner()

        result = runner.invoke(app, ['auth', 'login', '--api-key', mock_api_key])

        assert result.exit_code == 1
        assert "Failed to save API key" in result.stdout

    def test_login_keyboard_interrupt(self, temp_config_dir):
        """Test login keyboard interrupt handling"""
        runner = CliRunner()

        with patch('pingera_cli.commands.auth.Prompt.ask', side_effect=KeyboardInterrupt()):
            result = runner.invoke(app, ['auth', 'login', '--interactive'])

        assert result.exit_code == 1
        assert "Operation cancelled" in result.stdout

    def test_status_with_config_error(self, temp_config_dir):
        """Test status command when config reading fails"""
        runner = CliRunner()

        # Create invalid JSON config file
        config_file = os.path.join(temp_config_dir, 'config.json')
        with open(config_file, 'w') as f:
            f.write('invalid json content')

        with patch.dict(os.environ, {}, clear=True):
            with patch('pingera_cli.utils.config.get_api_key', return_value=None):
                result = runner.invoke(app, ['auth', 'status'])

        # Should still work due to fallback to default config
        assert result.exit_code == 0
        assert "❌ Not Authenticated" in result.stdout

    def test_login_no_api_key_no_interactive(self, temp_config_dir, mock_api_key):
        """Test login with no API key and not in interactive mode falls back to prompt"""
        runner = CliRunner()

        with patch('pingera_cli.commands.auth.Prompt.ask', return_value=mock_api_key):
            with patch('pingera_cli.utils.config.set_api_key', return_value=True):
                # When no --api-key is provided and --interactive is not used,
                # the command should still prompt for input
                result = runner.invoke(app, ['auth', 'login'])

        assert result.exit_code == 0
        assert "API key has been saved successfully" in result.stdout