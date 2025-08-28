
# Pingera Platform CLI 🚀

A beautiful Python CLI tool for the [Pingera Platform](https://pingera.ru) - built with typer and rich, distributed via pip and based on Pingera SDK.

[![PyPI version](https://badge.fury.io/py/pingera-cli.svg)](https://badge.fury.io/py/pingera-cli)
[![Python Support](https://img.shields.io/pypi/pyversions/pingera-cli.svg)](https://pypi.org/project/pingera-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- **Beautiful Terminal Output**: Powered by Rich library for colorful, formatted output
- **Modern CLI Interface**: Built with Typer for intuitive command-line interactions  
- **Pingera Platform Integration**: Seamlessly integrates with Pingera SDK for network monitoring
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Easy Installation**: Simple pip install with all dependencies managed
- **Configuration Management**: Flexible configuration with environment variables and config files

## 🚀 Installation

Install Pingera Platform CLI using pip:

```bash
pip install pingera-cli
```

## 🔐 Authentication

Before using the CLI, you need to authenticate with the Pingera Platform:

1. **Get your API key**: Visit [app.pingera.ru](https://app.pingera.ru) and create an API token in your account settings
2. **Login to the CLI**:
   ```bash
   pngr auth login --api-key your-api-key-here
   ```
3. **Verify authentication**:
   ```bash
   pngr auth status
   ```

Alternatively, you can set the API key as an environment variable:
```bash
export PINGERA_API_KEY=your-api-key-here
```

## 📖 Basic Usage

### List all monitoring checks
```bash
pngr checks list
```

### Get details of a specific check
```bash
pngr checks get <check-id>
```

### Create a new web check
```bash
pngr checks create \
  --name "My Website" \
  --type web \
  --url https://example.com \
  --interval 300
```

### Get check results
```bash
pngr checks results <check-id>
```

### Run an on-demand check
```bash
pngr checks run custom \
  --type web \
  --url https://example.com \
  --name "Quick Test"
```

### List available regions
```bash
pngr checks list-regions
```

### Filter regions by check type
```bash
pngr checks list-regions --check-type web
```

## 🔧 Configuration

The CLI stores configuration in `~/.config/pingera-cli/config.json`. You can manage settings with:

```bash
# Show current configuration
pngr config show

# Set default output format
pngr config set output_format json
```

## 📊 Output Formats

The CLI supports multiple output formats:

- **table** (default): Human-readable tables
- **json**: JSON format for scripting
- **yaml**: YAML format

```bash
# JSON output
pngr checks list --output json

# YAML output  
pngr checks list --output yaml
```

## 🌐 Platform Links

- **Pingera Platform**: [https://pingera.ru](https://pingera.ru)
- **Web Application**: [https://app.pingera.ru](https://app.pingera.ru)
- **Documentation**: [https://docs.pingera.com](https://docs.pingera.com)

## 🛠️ Development

```bash
# Clone the repository
git clone https://github.com/pingera/pingera-cli.git
cd pingera-cli

# Install in development mode
pip install -e .

# Test the CLI (after installation)
pngr --help

# Run tests
python -m pytest tests/
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/pingera/pingera-cli/issues)
- **Documentation**: [Pingera CLI Docs](https://docs.pingera.com/cli)
- **Platform Support**: [app.pingera.ru](https://app.pingera.ru)
