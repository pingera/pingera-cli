
"""
File utilities for PingeraCLI
"""

import os
import json
from typing import Dict, Any
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import typer


def is_url(file_path: str) -> bool:
    """Check if the file path is a URL"""
    try:
        result = urlparse(file_path)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def download_file_content(url: str) -> str:
    """Download content from a URL"""
    try:
        # Add a user agent to avoid being blocked by some servers
        req = Request(url, headers={'User-Agent': 'PingeraCLI/1.0'})
        
        with urlopen(req, timeout=30) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}: {response.reason}")
            
            content = response.read().decode('utf-8')
            return content
            
    except HTTPError as e:
        raise Exception(f"HTTP error {e.code}: {e.reason}")
    except URLError as e:
        raise Exception(f"URL error: {e.reason}")
    except Exception as e:
        raise Exception(f"Failed to download file: {str(e)}")


def parse_file_content(content: str, file_path: str) -> Dict[Any, Any]:
    """Parse file content as JSON or YAML"""
    if not content.strip():
        raise Exception(f"File content is empty: {file_path}")
    
    # Try to determine format from file extension or content
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext in ['.yaml', '.yml']:
        try:
            import yaml
            return yaml.safe_load(content)
        except ImportError:
            raise Exception("YAML support not available. Install with: pip install pyyaml")
        except yaml.YAMLError as e:
            raise Exception(f"Invalid YAML in file {file_path}: {str(e)}")
    else:
        # Default to JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in file {file_path}: {str(e)}")


def load_check_file(file_path: str) -> Dict[Any, Any]:
    """Load check configuration from local file or URL"""
    try:
        if is_url(file_path):
            # Download from URL
            content = download_file_content(file_path)
            return parse_file_content(content, file_path)
        else:
            # Load from local file
            if not os.path.exists(file_path):
                raise Exception(f"Check file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return parse_file_content(content, file_path)
            
    except Exception as e:
        # Re-raise with a more specific error message
        if "Check file not found" in str(e) or "File content is empty" in str(e) or "Invalid JSON" in str(e) or "Invalid YAML" in str(e):
            raise typer.Exit(1) from e
        else:
            raise Exception(f"Failed to load check file: {str(e)}") from e
