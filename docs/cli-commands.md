# Pingera CLI Commands Specification

## Overview

The `pngr` CLI provides a comprehensive interface to the Pingera monitoring platform. Commands are organized into logical groups based on the SDK's API modules.

## Global Options

These options are available for all commands:

```
--api-key <key>         API key for authentication (can also be used PINGERA_API_KEY env var)
--base-url <url>        API base URL (default: https://api.pingera.ru)
--output <format>       Output format: table, json, yaml (default: table)
--page-id <id>          Default page ID for status page operations (can also use PINGERA_PAGE_ID env var)
--verbose, -v           Enable verbose output
--help, -h              Show help message
--version, -V           Show version information
```

## Authentication Commands

### `pngr auth`
Manage authentication settings.

```bash
pngr auth login --api-key <key>           # Set API key
pngr auth login --bearer-token <token>    # Set bearer token
pngr auth status                          # Check authentication status
pngr auth logout                          # Clear stored credentials
```

## Checks Commands

### `pngr checks`
Manage monitoring checks.

```bash
# List checks
pngr checks list [--page <num>] [--page-size <size>] [--type <type>] [--status <status>] [--name <name>] [--group-id <id>]

# Get specific check
pngr checks get <check-id>

# Create check
pngr checks create --name <name> --type <type> [--url <url>] [--host <host>] [--port <port>] [--interval <seconds>] [--timeout <seconds>] [--parameters <json>] [--pw-script-file <path>]

# Update check
pngr checks update <check-id> [--name <name>] [--url <url>] [--host <host>] [--port <port>] [--interval <seconds>] [--timeout <seconds>] [--active/--inactive] [--parameters <json>] [--pw-script-file <path>]

# Delete check
pngr checks delete <check-id> [--confirm]

# Assign check to group
pngr checks assign-group <check-id> [--group-id <group-id>]

# Get check results
pngr checks results <check-id> [--from <date>] [--to <date>] [--page <num>] [--page-size <size>]

# Get detailed result information
pngr checks result <check-id> <result-id>

# Manage on-demand check jobs
pngr checks jobs list
pngr checks jobs get <job-id>
```

### `pngr checks groups`
Manage check groups for organizing checks.

```bash
# List all check groups
pngr checks groups list

# Get a specific check group
pngr checks groups get <group_id>

# Create a new check group
pngr checks groups create "API Endpoints" --description "All API endpoint checks" --color "#4F46E5"

# Update a check group
pngr checks groups update <group_id> --name "Updated Name" --description "Updated description"

# Delete a check group
pngr checks groups delete <group_id>
```

### `pngr checks secrets`
Manage secret associations for checks to inject environment variables.

```bash
# List all secrets associated with a check
pngr checks secrets list <check_id>

# Add a secret to a check with environment variable name
pngr checks secrets add <check_id> <secret_id> DATABASE_PASSWORD

# Remove a secret association from a check
pngr checks secrets remove <check_id> <secret_id>

# Remove a secret without confirmation
pngr checks secrets remove <check_id> <secret_id> --force

# Replace all secret associations for a check
pngr checks secrets update-all <check_id> --associations '[{"secret_id": "sec123", "env_variable": "DB_PASS"}, {"secret_id": "sec456", "env_variable": "API_KEY"}]'
```

## On-Demand Checks Commands 

### `pngr checks run`
Execute checks on demand.

```bash
# Execute custom check
pngr checks run custom [--url <url>] --type <type> [--host <host>] [--port <port>] [--timeout <seconds>] [--name <name>] [--parameters <json>] [--pw-script-file <path>] [--wait-for-result]

# Execute existing check
pngr checks run existing <check-id> [--wait-for-result]

# List on-demand checks
pngr checks run list [--page <num>] [--page-size <size>]
```

### `pngr checks jobs`
Manage check jobs.

```bash
# Get job result
pngr checks jobs result <job-id>

# List check jobs
pngr checks jobs list
```

## Alerts Commands (soon)

### `pngr alerts`
Manage alerts and notifications.

```bash
# List alerts
pngr alerts list [--page <num>] [--page-size <size>] [--status <status>]

# Get specific alert
pngr alerts get <alert-id>

# Create alert
pngr alerts create --name <name> --type <type> [--channels <channels>] [--enabled]

# Update alert
pngr alerts update <alert-id> [--name <name>] [--enabled/--disabled]

# Delete alert
pngr alerts delete <alert-id> [--confirm]

# Get alert statistics
pngr alerts stats

# Manage alert channels
pngr alerts channels list
pngr alerts channels create --name <name> --type <type> --config <json>
pngr alerts channels delete <channel-id>

# Manage alert rules
pngr alerts rules list
pngr alerts rules create --name <name> --conditions <json>
pngr alerts rules delete <rule-id>
```

## Heartbeats Commands (soon)

### `pngr heartbeats`
Manage heartbeat monitoring.

```bash
# List heartbeats
pngr heartbeats list [--page <num>] [--page-size <size>] [--status <status>]

# Get specific heartbeat
pngr heartbeats get <heartbeat-id>

# Create heartbeat
pngr heartbeats create --name <name> --interval <seconds> [--grace-period <seconds>]

# Update heartbeat
pngr heartbeats update <heartbeat-id> --name <name> --interval <seconds>

# Delete heartbeat
pngr heartbeats delete <heartbeat-id> [--confirm]

# Send heartbeat ping
pngr heartbeats ping <heartbeat-id>

# Get heartbeat logs
pngr heartbeats logs <heartbeat-id> [--from <date>] [--to <date>] [--page <num>]
```

## Status Pages Commands (soon)

### `pngr pages`
Manage status pages.

```bash
# List status pages
pngr pages list [--page <num>] [--page-size <size>]

# Get specific status page
pngr pages get <page-id>

# Create status page
pngr pages create --name <name> [--description <desc>] [--subdomain <sub>] [--theme <theme>]

# Update status page
pngr pages update <page-id> --name <name> --description <desc> --theme <theme>

# Delete status page
pngr pages delete <page-id> [--confirm]
```

### `pngr components`
Manage status page components.

```bash
# List components
pngr components list [--page-id <id>] [--page <num>] [--page-size <size>]

# Get specific component
pngr components get <component-id> [--page-id <id>]

# Create component
pngr components create --name <name> [--description <desc>] [--status <status>] [--page-id <id>]

# Update component
pngr components update <component-id> --name <name> --description <desc> --page-id <id>

# Delete component
pngr components delete <component-id> [--page-id <id>] [--confirm]

# Update component status
pngr components status <component-id> --status <status> [--page-id <id>]

# Get component uptime
pngr components uptime <component-id> [--page-id <id>] [--from <date>] [--to <date>]

# Bulk update component uptime
pngr components uptime-bulk --file <json-file> [--page-id <id>]
```

### `pngr incidents`
Manage incidents and maintenance.

```bash
# List incidents
pngr incidents list [--page-id <id>] [--page <num>] [--page-size <size>] [--status <status>]

# Get specific incident
pngr incidents get <incident-id> [--page-id <id>]

# Create incident
pngr incidents create --name <name> --body <text> --status <status> --impact <impact> [--page-id <id>]

# Update incident
pngr incidents update <incident-id> --name <name> --body <text> --status <status> --page-id <id>

# Delete incident
pngr incidents delete <incident-id> [--page-id <id>] [--confirm]

# Manage incident updates
pngr incidents updates list <incident-id> [--page-id <id>]
pngr incidents updates create <incident-id> --body <text> --status <status> [--page-id <id>]
pngr incidents updates get <incident-id> <update-id> [--page-id <id>]
pngr incidents updates update <incident-id> <update-id> --body <text> [--page-id <id>]
pngr incidents updates delete <incident-id> <update-id> [--page-id <id>] [--confirm]
```

## 📄 Check Configuration Files

You can create checks from JSON or YAML configuration files using the `--from-file` option:

### JSON Format
```json
{
  "name": "My API Check",
  "type": "api",
  "url": "https://api.example.com/health",
  "interval": 300,
  "timeout": 30,
  "parameters": {
    "regions": ["US", "EU"],
    "http_request": {
      "method": "POST",
      "headers": {
        "Authorization": "Bearer token123",
        "Content-Type": "application/json"
      },
      "body": "{\"check\": \"health\"}"
    }
  }
}
```

### YAML Format
```yaml
name: "My Synthetic Check"
type: "synthetic"
interval: 600
timeout: 60
parameters:
  regions:
    - "US"
    - "EU"
  pw_script: |
    const { test, expect } = require('@playwright/test');
    test('login test', async ({ page }) => {
      await page.goto('https://example.com/login');
      await page.fill('#username', 'testuser');
      await page.fill('#password', 'password');
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/dashboard/);
    });
# Marketplace fields (ignored by CLI, used by web interface)
marketplace:
  tags: ["authentication", "login"]
  description: "Tests user login functionality"
  category: "user-flows"
```

### Field Priority
When using `--from-file` with command line options:
- Command line options override file values
- File provides defaults for unspecified options
- Required validations still apply
- Non-SDK fields (like `marketplace`, custom fields) are ignored and not sent to the API
- CLI-specific fields like `pw_script_file` are processed but not sent to the SDK

### Create a new check
```bash
# From command line options
pngr checks create --name "My Website" --type web --url "https://example.com"

# From configuration file
pngr checks create --from-file check-config.json
pngr checks create --from-file check-config.yaml

# Combine file and command line (command line options override file values)
pngr checks create --from-file check-config.json --name "Override Name"
```

### Run on-demand checks
```bash
# From command line options
pngr checks run custom --url https://example.com --type web --wait-for-result

# From configuration file
pngr checks run custom --from-file check-config.json --wait-for-result
pngr checks run custom --from-file check-config.yaml --wait-for-result

# Combine file and command line (command line options override file values)
pngr checks run custom --from-file check-config.json --name "Override Name" --wait-for-result
```

## 🔐 Secrets Management

Manage organization secrets for use in monitoring checks:

```bash
# List all secrets
pngr secrets list

# List secrets with pagination
pngr secrets list --page 2 --page-size 50

# Get a specific secret by ID
pngr secrets get sec123abc456

# Create a new secret (will prompt for value securely)
pngr secrets create "DATABASE_PASSWORD"

# Create a secret with value provided via option
pngr secrets create "API_KEY" --value "your-secret-value"

# Update a secret's value (will prompt for new value securely)
pngr secrets update sec123abc456

# Update a secret with value provided via option
pngr secrets update sec123abc456 --value "new-secret-value"

# Delete a secret (with confirmation)
pngr secrets delete sec123abc456

# Delete a secret without confirmation
pngr secrets delete sec123abc456 --force
```

**Note:** Secret values are hidden in list views for security. Only individual secret retrieval shows the actual value (when permissions allow).

## Configuration Commands

### `pngr config`
Manage CLI configuration.

```bash
pngr config show                          # Show current configuration
pngr config set <key> <value>            # Set configuration value
pngr config get <key>                    # Get configuration value
pngr config unset <key>                  # Remove configuration value
pngr config reset                        # Reset to defaults
```

## Utility Commands

### `pngr info`
Show system and SDK information.

```bash
pngr info                                # Show CLI and SDK information
pngr info version                        # Show version information only
```

## Common Patterns

### Filtering and Pagination
Most list commands support:
- `--page <num>`: Page number (default: 1)
- `--page-size <size>`: Items per page (default: 20, max: 100)
- `--status <status>`: Filter by status
- `--type <type>`: Filter by type

### Date Ranges
Commands that support time-based filtering use:
- `--from <date>`: Start date (ISO 8601 format)
- `--to <date>`: End date (ISO 8601 format)

Date formats supported:
- ISO 8601: `2023-01-01T00:00:00Z`
- Date only: `2023-01-01`
- Relative: `1h`, `1d`, `1w` (ago from now)

### Output Formats
- `table`: Human-readable table (default)
- `json`: JSON format
- `yaml`: YAML format

### Confirmation
Destructive operations support:
- `--confirm`: Skip confirmation prompt
- `--dry-run`: Show what would be done without executing

## Environment Variables

- `PINGERA_API_KEY`: Default API key
- `PINGERA_BEARER_TOKEN`: Default bearer token  
- `PINGERA_PAGE_ID`: Default status page ID
- `PINGERA_BASE_URL`: Default API base URL
- `PNGR_OUTPUT_FORMAT`: Default output format
- `PNGR_CONFIG_DIR`: Configuration directory

## Configuration File

Configuration stored in `~/.config/pngr/config.yaml`:

```yaml
auth:
  api_key: "your-api-key"
  bearer_token: "your-bearer-token"
  base_url: "https://api.pingera.ru"

defaults:
  page_id: "your-default-page-id"
  output_format: "table"
  page_size: 20

display:
  colors: true
  timestamps: "relative"  # relative, absolute, none
```

## Examples

```bash
# Quick setup
pngr auth login --api-key your-api-key-here
pngr config set defaults.page_id your-page-id

# List all active checks
pngr checks list --status active

# Create a web check
pngr checks create --name "My Website" --type web --url "https://example.com"

# Create a TCP check
pngr checks create --name "Database Connection" --type tcp --host db.example.com --port 5432

# Create a synthetic check with Playwright script
pngr checks create --name "Login Flow" --type synthetic --pw-script-file ./scripts/login-test.js --parameters '{"regions": ["US", "EU"]}'

# Create an SSL certificate check
pngr checks create --name "SSL Monitor" --type ssl --url https://example.com

# Run an on-demand web check
pngr checks run custom --url https://example.com --type web --timeout 30

# Run an on-demand TCP check and wait for result
pngr checks run custom --host db.example.com --port 5432 --type tcp --name "Database Connection Test" --wait-for-result

# Run an on-demand synthetic check with Playwright script and wait for result
pngr checks run custom --type synthetic --pw-script-file ./scripts/login-test.js --name "Login Flow Test" --parameters '{"regions": ["US", "EU"]}' --wait-for-result

# Run an on-demand SSL certificate check
pngr checks run custom --url https://example.com --type ssl --name "SSL Certificate Test"

# Execute existing check and wait for result
pngr checks run existing check_123 --wait-for-result

# Create an incident
pngr incidents create --name "Database Issues" --body "Investigating connectivity" --status investigating --impact major

# Update component status  
pngr components status comp_123 --status degraded_performance

# Update check with custom parameters (Playwright script and regions)
pngr checks update check_123 --parameters '{"pw_script": "const { test, expect } = require(\"@playwright/test\"); test(\"example\", async ({ page }) => { await page.goto(\"https://example.com\"); await expect(page).toHaveTitle(/Example/); });", "regions": ["US", "EU"]}'

# Update check with Playwright script from file
pngr checks update check_123 --pw-script-file ./scripts/my-test.js --parameters '{"regions": ["US", "EU"]}'

# Update check interval and make it active
pngr checks update check_123 --interval 600 --active

# Get check results for last 24 hours
pngr checks results check_123 --from 1d

# List all check groups
pngr checks groups list

# Create a new check group
pngr checks groups create --name "Production APIs" --description "Critical production API endpoints" --color "#FF5733" --position 1

# Get specific group details
pngr checks groups get group_123

# Update a group
pngr checks groups update group_123 --name "Updated Group Name" --color "#4F46E5"

# Delete a group
pngr checks groups delete group_123

# Get checks in a specific group
pngr checks groups checks group_123

# Assign a check to a group
pngr checks assign-group check_123 --group-id group_456

# Remove check from group
pngr checks assign-group check_123 --group-id null

# Export incidents as JSON
pngr incidents list --output json > incidents.json