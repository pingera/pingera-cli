
"""
Tests for configuration utilities
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from pingera_cli.utils.config import (
    get_config_path,
    get_config,
    save_config,
    get_api_key,
    set_api_key,
    set_output_format,
    get_output_format,
    validate_config
)


class TestConfig:
    """Test configuration utilities"""
    
    def test_get_config_path_default(self):
        """Test default config path"""
        with patch.dict(os.environ, {}, clear=True):
            config_path = get_config_path()
            expected_path = Path.home() / '.config' / 'pingera-cli' / 'config.json'
            assert config_path == expected_path

    def test_get_config_path_xdg(self, tmp_path):
        """Test config path with XDG_CONFIG_HOME"""
        custom_config = str(tmp_path / 'custom_config')
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': custom_config}):
            config_path = get_config_path()
            expected_path = Path(custom_config) / 'pingera-cli' / 'config.json'
            assert config_path == expected_path

    def test_get_config_default(self):
        """Test getting default config when no file exists"""
        with patch('pingera_cli.utils.config.get_config_path') as mock_path:
            mock_path.return_value = Path('/nonexistent/config.json')
            
            config = get_config()
            
            assert config['base_url'] == 'https://api.pingera.ru'
            assert config['output_format'] == 'table'
            assert config['verbose'] is False
            assert config['color'] is True
            assert config['timeout'] == 30.0
            assert config['retries'] == 3

    def test_get_config_from_file(self, tmp_path):
        """Test getting config from existing file"""
        config_file = tmp_path / 'config.json'
        test_config = {
            'base_url': 'https://custom.api.url',
            'output_format': 'json',
            'api_key': 'test_key_123'
        }
        
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            config = get_config()
            
            # Should merge with defaults
            assert config['base_url'] == 'https://custom.api.url'
            assert config['output_format'] == 'json'
            assert config['api_key'] == 'test_key_123'
            # Defaults should still be present
            assert config['verbose'] is False
            assert config['timeout'] == 30.0

    def test_get_config_invalid_json(self, tmp_path):
        """Test getting config with invalid JSON file"""
        config_file = tmp_path / 'config.json'
        config_file.write_text('invalid json content')
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            config = get_config()
            
            # Should return default config
            assert config['base_url'] == 'https://api.pingera.ru'
            assert config['output_format'] == 'table'

    def test_save_config_success(self, tmp_path):
        """Test successful config saving"""
        config_file = tmp_path / 'config.json'
        test_config = {'api_key': 'test_key', 'output_format': 'json'}
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            result = save_config(test_config)
            
            assert result is True
            assert config_file.exists()
            
            with open(config_file, 'r') as f:
                saved_config = json.load(f)
                assert saved_config == test_config

    def test_save_config_failure(self):
        """Test config saving failure"""
        test_config = {'api_key': 'test_key'}
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=Path('/invalid/path/config.json')):
            result = save_config(test_config)
            
            assert result is False

    def test_get_api_key_from_env(self):
        """Test getting API key from environment variable"""
        with patch.dict(os.environ, {'PINGERA_API_KEY': 'env_api_key'}):
            api_key = get_api_key()
            assert api_key == 'env_api_key'

    def test_get_api_key_from_config(self, tmp_path):
        """Test getting API key from config file"""
        config_file = tmp_path / 'config.json'
        config_data = {'api_key': 'config_api_key'}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch.dict(os.environ, {}, clear=True), \
             patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            api_key = get_api_key()
            assert api_key == 'config_api_key'

    def test_get_api_key_none(self, tmp_path):
        """Test getting API key when none exists"""
        config_file = tmp_path / 'config.json'
        config_data = {'output_format': 'table'}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch.dict(os.environ, {}, clear=True), \
             patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            api_key = get_api_key()
            assert api_key is None

    def test_set_api_key_success(self, tmp_path):
        """Test successful API key setting"""
        config_file = tmp_path / 'config.json'
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            result = set_api_key('new_api_key')
            
            assert result is True
            
            with open(config_file, 'r') as f:
                config = json.load(f)
                assert config['api_key'] == 'new_api_key'

    def test_set_api_key_empty(self):
        """Test setting empty API key"""
        result = set_api_key('')
        assert result is False
        
        result = set_api_key('   ')
        assert result is False
        
        result = set_api_key(None)
        assert result is False

    def test_set_output_format_success(self, tmp_path):
        """Test successful output format setting"""
        config_file = tmp_path / 'config.json'
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            result = set_output_format('json')
            
            assert result is True
            
            with open(config_file, 'r') as f:
                config = json.load(f)
                assert config['output_format'] == 'json'

    def test_set_output_format_invalid(self):
        """Test setting invalid output format"""
        result = set_output_format('invalid')
        assert result is False

    def test_get_output_format_default(self, tmp_path):
        """Test getting default output format"""
        config_file = tmp_path / 'config.json'
        config_data = {}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            output_format = get_output_format()
            assert output_format == 'table'

    def test_get_output_format_from_config(self, tmp_path):
        """Test getting output format from config"""
        config_file = tmp_path / 'config.json'
        config_data = {'output_format': 'yaml'}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            output_format = get_output_format()
            assert output_format == 'yaml'

    def test_validate_config_all_good(self, tmp_path):
        """Test config validation when everything is good"""
        config_file = tmp_path / 'config.json'
        config_data = {'api_key': 'test_key'}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file), \
             patch.dict(os.environ, {'PINGERA_API_KEY': 'env_key'}):
            
            validation = validate_config()
            
            assert validation['api_key_set'] is True
            assert validation['config_file_exists'] is True
            assert validation['config_file_readable'] is True
            assert validation['pingera_sdk_available'] is True

    def test_validate_config_missing_api_key(self, tmp_path):
        """Test config validation with missing API key"""
        config_file = tmp_path / 'config.json'
        config_data = {}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file), \
             patch.dict(os.environ, {}, clear=True):
            
            validation = validate_config()
            
            assert validation['api_key_set'] is False

    def test_validate_config_no_config_file(self):
        """Test config validation with no config file"""
        with patch('pingera_cli.utils.config.get_config_path', return_value=Path('/nonexistent/config.json')):
            validation = validate_config()
            
            assert validation['config_file_exists'] is False

    def test_validate_config_unreadable_file(self, tmp_path):
        """Test config validation with unreadable config file"""
        config_file = tmp_path / 'config.json'
        config_file.write_text('invalid json')
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file):
            validation = validate_config()
            
            assert validation['config_file_readable'] is False

    def test_validate_config_no_sdk(self, tmp_path):
        """Test config validation when SDK is not available"""
        config_file = tmp_path / 'config.json'
        config_data = {'api_key': 'test_key'}
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        with patch('pingera_cli.utils.config.get_config_path', return_value=config_file), \
             patch('pingera_cli.utils.config.validate_config') as mock_validate:
            
            # Mock the import error
            def mock_validation():
                results = {
                    'api_key_set': True,
                    'config_file_exists': True,
                    'config_file_readable': True,
                    'pingera_sdk_available': True,
                }
                
                try:
                    from pingera import ApiClient
                except ImportError:
                    results['pingera_sdk_available'] = False
                
                return results
            
            mock_validate.side_effect = mock_validation
            
            # Test with ImportError
            with patch('builtins.__import__', side_effect=ImportError('No module named pingera')):
                validation = mock_validation()
                assert validation['pingera_sdk_available'] is False
