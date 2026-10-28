# Pingera Platform CLI 🚀

A beautiful Python CLI tool for the [Pingera Platform](https://pingera.ru) - built with typer and rich, distributed via pip and based on Pingera SDK.

[![PyPI version](https://badge.fury.io/py/pingera-cli.svg)](https://badge.fury.io/py/pingera-cli)
[![Python Support](https://img.shields.io/pypi/pyversions/pingera-cli.svg)](https://pypi.org/project/pingera-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- **Beautiful Terminal Output**: Powered by Rich library for colorful, formatted output
- **Modern CLI Interface**: Built with Typer for intuitive command-line interactions  
- **Pingera Platform Integration**: Manage checks, uptime and performance analytics, alert rules and channels, and status pages (components, incidents, maintenance, postmortems) through the Pingera SDK
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Easy Installation**: Simple pip install with all dependencies managed
- **Configuration Management**: Flexible configuration with environment variables and config files
- **Secrets Management**: Manage organization secrets for monitoring checks

## 🚀 Installation

Install Pingera Platform CLI using pip (requires Python 3.10+):

```bash
pip install pingera-cli
```

The CLI is built on [pingera-sdk](https://pypi.org/project/pingera-sdk/) 1.2+, which is installed automatically.

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

### Schedule a check with cron
```bash
# Run on weekdays at 09:00 instead of a fixed interval
pngr checks create --name "Morning check" --type web --url https://example.com --cron "0 9 * * 1-5"

# Switch an existing check between cron and interval scheduling
pngr checks update <check-id> --cron "*/15 * * * *"
pngr checks update <check-id> --interval 300
```

### Get check results
```bash
pngr checks results <check-id>
```

### Uptime and performance
```bash
# Uptime over the last 7 days, with hour-by-hour detail
pngr checks uptime <check-id> --from 7d --hourly

# p95/p99 response times per region
pngr checks response-times <check-id> --from 24h

# Success rate per region across all checks
pngr checks stats --from 7d
```

### Run an on-demand check
```bash
pngr checks run custom \
  --type web \
  --url https://example.com \
  --name "Quick Test"
```

### Manage check groups
```bash
# List all check groups
pngr checks groups list

# Create a new group
pngr checks groups create \
  --name "Production APIs" \
  --description "Critical production endpoints" \
  --color "#FF5733"

# Assign a check to a group
pngr checks assign-group check_123 --group-id group_456

# Remove a check from its group
pngr checks assign-group check_123 --group-id null
```

### Alerts
```bash
# Create a notification channel and a rule that alerts after 3 consecutive failures
pngr alerts channels create --name "On-call" --email oncall@example.com
pngr alerts rules create --name "API down" --check <check-id> --count 3 --channel <channel-id>

# See what is firing and acknowledge it
pngr alerts list --status firing
pngr alerts ack <alert-id>
```

### Status pages
```bash
# Post an incident and follow-up updates
pngr pages incidents create --page-id <page-id> --name "API errors" --status investigating --impact major
pngr pages incidents updates add <incident-id> --page-id <page-id> --status resolved --body "Fixed"

# Schedule maintenance
pngr pages incidents schedule-maintenance --page-id <page-id> --name "DB upgrade" --start +24h --end +26h

# Component uptime for the whole page
pngr pages components uptime-report --page-id <page-id> --from 2026-01-01
```

See [docs/cli-commands.md](docs/cli-commands.md) for the full command reference.

### Secrets Management

```bash
# List organization secrets
pngr secrets list

# Create a new secret
pngr secrets create "DATABASE_PASSWORD"

# Update a secret's value
pngr secrets update sec123abc456

# Delete a secret
pngr secrets delete sec123abc456
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

The CLI stores configuration in `~/.config/pingera-cli/config.json` (or `$XDG_CONFIG_HOME/pingera-cli/config.json`). You can manage settings with:

```bash
# Show current configuration
pngr config --show

# Set the default output format
pngr config --output-format json

# Point the CLI at a different API endpoint
pngr config --base-url https://api.pingera.ru
```

## 📊 Output Formats

The CLI supports multiple output formats:

- **table** (default): Human-readable tables
- **json**: JSON format for scripting
- **yaml**: YAML format

`--output`/`-o` is a global option, so it goes before the command. It applies to that invocation only; use `pngr config --output-format` to change the default.

```bash
# JSON output
pngr -o json checks list

# YAML output
pngr -o yaml checks list
```

In `json`/`yaml` mode, stdout contains only the data, and status messages go to stderr, so output can be piped safely (for example, `pngr -o json checks list | jq '.checks[].id'`).

## 🌐 Platform Links

- **Pingera Platform**: [https://pingera.ru](https://pingera.ru)
- **Web Application**: [https://app.pingera.ru](https://app.pingera.ru)
- **Documentation**: [https://docs.pingera.ru](https://docs.pingera.ru)

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
- **Documentation**: [Pingera CLI Docs](https://docs.pingera.ru/devs/cli)
- **Platform Support**: [app.pingera.ru](https://app.pingera.ru)