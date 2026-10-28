# Pingera CLI Commands Specification

## Overview

The `pngr` CLI provides a comprehensive interface to the Pingera monitoring platform. Commands are organized into logical groups based on the SDK's API modules.

## Global Options

These options are available for all commands:

```
--api-key <key>         API key for authentication (can also be used PINGERA_API_KEY env var)
--base-url <url>        API base URL (default: https://api.pingera.ru)
--output <format>       Output format for this invocation: table, json, yaml (default: configured format, or table)
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
pngr checks create --name <name> --type <type> [--url <url>] [--host <host>] [--port <port>] [--interval <seconds> | --cron <expression>] [--timeout <seconds>] [--parameters <json>] [--pw-script-file <path>]

# Update check
pngr checks update <check-id> [--name <name>] [--url <url>] [--host <host>] [--port <port>] [--interval <seconds> | --cron <expression>] [--timeout <seconds>] [--active/--inactive] [--parameters <json>] [--pw-script-file <path>]

# Delete check
pngr checks delete <check-id> [--confirm]

# Assign check to group
pngr checks assign-group <check-id> [--group-id <group-id>]

# Get check results (dates: ISO 8601 or relative like 30m, 24h, 7d)
pngr checks results <check-id> [--from <date>] [--to <date>] [--page <num>] [--page-size <size>]

# Get detailed result information
pngr checks result <result-id> [--verbose]

# Uptime percentage, average response time and an hourly status strip
pngr checks uptime <check-id> [--from <date>] [--to <date>] [--hourly]

# Status periods (when the check went ok/failed/degraded and for how long)
pngr checks status-history <check-id> [--page <num>] [--page-size <size>]

# Average / p95 / p99 response times per region
pngr checks response-times <check-id> [--from <date>] [--to <date>] [--region <region>] [--status <status>] [--buckets]

# Result counts by status per region, for one check or all checks
pngr checks stats [<check-id>] [--from <date>] [--to <date>] [--region <region>] [--type <type>] [--result-type regular|on_demand] [--with-alerts|--without-alerts] [--buckets]

# Manage on-demand check jobs
pngr checks jobs list
pngr checks jobs status <job-id>
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

## Alerts Commands

### `pngr alerts`
🔔 Alerts: fired alerts, alert rules and notification channels

```bash
# List fired alerts, newest first
pngr alerts list [--status <status>] [--check <check-id>] [--severity <severity>] [--from <start>] [--to <end>] [--page <page>] [--per-page <per-page>]

# Show an alert with its rule, check, timeline and triggering results
pngr alerts get <alert-id>

# Acknowledge a firing alert
pngr alerts ack <alert-id>

# Manually resolve an active alert
pngr alerts resolve <alert-id>

# Show the notification delivery log of an alert, grouped by channel
pngr alerts notifications <alert-id>

# Show active/recent alert counts, severity breakdown and enabled rules/channels
pngr alerts stats
```

### `pngr alerts rules`
📏 Manage alert rules (when to alert and whom to notify)

```bash
# List alert rules
pngr alerts rules list [--check <check-id>] [--enabled/--disabled]

# Show a rule: its check, trigger condition, multi-region mode and notified channels
pngr alerts rules get <rule-id>

# Create an alert rule for a check
pngr alerts rules create [--from-file <from-file>] [--name <name>] [--check <check-id>] [--condition <condition>] [--count <count>] [--threshold <threshold>] [--window <window>] [--params <params>] [--severity <severity>] [--channel <channels>...] [--cooldown <cooldown>] [--auto-resolve/--no-auto-resolve] [--regions <regions>] [--regions-count <regions-count>] [--enabled/--disabled]

# Update an alert rule (only the given fields change; the check can't be changed)
pngr alerts rules update <rule-id> [--from-file <from-file>] [--name <name>] [--condition <condition>] [--count <count>] [--threshold <threshold>] [--window <window>] [--params <params>] [--severity <severity>] [--channel <channels>...] [--cooldown <cooldown>] [--auto-resolve/--no-auto-resolve] [--regions <regions>] [--regions-count <regions-count>] [--enabled/--disabled]

# Enable an alert rule
pngr alerts rules enable <rule-id>

# Disable (pause) an alert rule without deleting it
pngr alerts rules disable <rule-id>

# Delete an alert rule and its alert history
pngr alerts rules delete <rule-id> [--confirm]
```

### `pngr alerts channels`
📣 Manage alert notification channels

```bash
# List alert channels (secrets masked)
pngr alerts channels list [--type <channel-type>]

# Show an alert channel and its configuration (secrets masked)
pngr alerts channels get <channel-id>

# Create an alert channel
pngr alerts channels create [--from-file <from-file>] [--name <name>] [--type <channel-type>] [--email <emails>...] [--url <url>] [--method <method>] [--header <headers>...] [--timeout <timeout>] [--chat-id <chat-id>] [--phone <phones>...] [--page-id <page-id>] [--component-id <component-id>] [--config <config>] [--enabled/--disabled] [--test]

# Update an alert channel (only the given fields change; the type can't be changed)
pngr alerts channels update <channel-id> [--from-file <from-file>] [--name <name>] [--email <emails>...] [--url <url>] [--method <method>] [--header <headers>...] [--timeout <timeout>] [--chat-id <chat-id>] [--phone <phones>...] [--page-id <page-id>] [--component-id <component-id>] [--config <config>] [--enabled/--disabled]

# Delete an alert channel (it must not be used by any alert rule)
pngr alerts channels delete <channel-id> [--confirm]

# Send a test notification through a saved channel, or through an unsaved configuration
pngr alerts channels test [<channel-id>] [--name <name>] [--type <channel-type>] [--email <emails>...] [--url <url>] [--method <method>] [--header <headers>...] [--timeout <timeout>] [--chat-id <chat-id>] [--config <config>]
```

## Heartbeats Commands

Heartbeat monitoring is not available in the CLI yet; use the web app or the SDK (`HeartbeatsApi`).

## Status Pages Commands

Commands that act on a page take `--page-id`/`-p`. Times accept ISO 8601 or relative values (e.g. `7d`).

### `pngr pages`
📄 Manage status pages

```bash
# List status pages
pngr pages list [--page <page>] [--page-size <page-size>]

# Get specific page details
pngr pages get <page-id>

# Create a new status page
pngr pages create --name <name> [--subdomain <subdomain>] [--domain <domain>] [--description <description>] [--headline <headline>] [--url <url>] [--support-url <support-url>] [--private] [--password-protected] [--timezone <time-zone>] [--language <language>] [--country <country>] [--hidden-from-search] [--ga-id <google-analytics-id>] [--ym-id <yandex-metrica-id>] [--notifications-email <notifications-from-email>] [--email-footer <notifications-email-footer>] [--allow-email-subscribers/--no-email-subscribers] [--allow-sms-subscribers] [--allow-webhook-subscribers] [--allow-rss/--no-rss] [--template <template>]

# Update an existing status page
pngr pages update <page-id> [--name <name>] [--subdomain <subdomain>] [--domain <domain>] [--description <description>] [--headline <headline>] [--url <url>] [--support-url <support-url>] [--public/--private] [--password-protected/--no-password] [--timezone <time-zone>] [--language <language>] [--country <country>] [--hidden-from-search/--visible-in-search] [--ga-id <google-analytics-id>] [--ym-id <yandex-metrica-id>] [--notifications-email <notifications-from-email>] [--email-footer <notifications-email-footer>] [--allow-email-subscribers/--no-email-subscribers] [--allow-sms-subscribers/--no-sms-subscribers] [--allow-webhook-subscribers/--no-webhook-subscribers] [--allow-rss/--no-rss] [--template <template>]

# Delete a status page
pngr pages delete <page-id> [--confirm]

# Show page status, incidents, and components by domain
pngr pages show <domain>

# List the page templates available for 'pages create/update --template'
pngr pages templates
```

### `pngr pages components`
🔧 Manage status page components

```bash
# List components for a status page
pngr pages components list --page-id <page-id>

# Get specific component details
pngr pages components get <component-id> --page-id <page-id>

# Create a new component
pngr pages components create --name <name> --page-id <page-id> [--description <description>] [--status <status>] [--group-id <group-id>] [--position <position>] [--showcase] [--only-if-degraded] [--start-date <start-date>]

# Update an existing component
pngr pages components update <component-id> --page-id <page-id> [--name <name>] [--description <description>] [--status <status>] [--group-id <group-id>] [--position <position>] [--showcase/--no-showcase] [--only-if-degraded/--always-show]

# Delete a component
pngr pages components delete <component-id> --page-id <page-id> [--confirm]

# Get uptime data for a specific component
pngr pages components uptime <component-id> --page-id <page-id> [--start <start>] [--end <end>] [--verbose]

# List the valid component statuses
pngr pages components statuses

# Show uptime % and outage time for all (or selected) components of a page
pngr pages components uptime-report --page-id <page-id> [--component-id <component-ids>...] [--from <start>] [--to <end>] [--include-groups]
```

### `pngr pages component-groups`
🗂  Manage component groups on a status page

```bash
# List component groups with the components they contain
pngr pages component-groups list --page-id <page-id>

# Show a component group and its member components
pngr pages component-groups get <group-id> --page-id <page-id>

# Create a component group, optionally moving existing components into it
pngr pages component-groups create --page-id <page-id> --name <name> [--description <description>] [--position <position>] [--component-id <component-ids>...]

# Update a component group (PATCH) and/or change which components belong to it
pngr pages component-groups update <group-id> --page-id <page-id> [--name <name>] [--description <description>] [--position <position>] [--add-component <add>...] [--remove-component <remove>...]

# Delete a component group (member components are kept and become ungrouped)
pngr pages component-groups delete <group-id> --page-id <page-id> [--confirm]
```

### `pngr pages incidents`
🚨 Manage status page incidents

```bash
# List incidents for a status page
pngr pages incidents list --page-id <page-id> [--component-id <component-id>] [--unresolved] [--maintenance]

# Get specific incident details
pngr pages incidents get <incident-id> --page-id <page-id> [--verbose]

# Create a new incident
pngr pages incidents create --name <name> --status <status> --page-id <page-id> [--body <body>] [--impact <impact>] [--components <components>] [--no-notifications]

# Update an existing incident
pngr pages incidents update <incident-id> --page-id <page-id> [--name <name>] [--status <status>] [--body <body>] [--impact <impact>] [--components <components>]

# Delete an incident
pngr pages incidents delete <incident-id> --page-id <page-id> [--confirm]

# List unresolved incidents (not resolved)
pngr pages incidents unresolved --page-id <page-id> [--component-id <component-id>]

# List scheduled maintenance windows
pngr pages incidents maintenance --page-id <page-id> [--component-id <component-id>]

# Show valid incident statuses, maintenance statuses and impacts
pngr pages incidents reference

# Record an incident that already happened (with its timeline) so it shows in history and uptime
pngr pages incidents log-past --page-id <page-id> --name <name> --impact <impact> [--started <started>] [--resolved <resolved>] [--body <body>] [--resolution <resolution>] [--component <component>...] [--updates-file <updates-file>] [--notify/--no-notify]

# Schedule a maintenance window (status 'scheduled', impact 'maintenance')
pngr pages incidents schedule-maintenance --page-id <page-id> --name <name> --start <start> --end <end> [--body <body>] [--component-id <component-ids>...] [--notify/--no-notify] [--auto-start/--no-auto-start] [--auto-complete/--no-auto-complete] [--auto-component-status/--no-auto-component-status] [--notify-transitions/--no-notify-transitions] [--remind/--no-remind] [--reminders <reminders>]
```

### `pngr pages incidents updates`
🧾 Manage the update timeline of an incident

```bash
# List all updates of an incident (newest first)
pngr pages incidents updates list <incident-id> --page-id <page-id>

# Post a new update to an incident (changes its status, component statuses and notifies subscribers)
pngr pages incidents updates add <incident-id> --page-id <page-id> [--status <status>] [--body <body>] [--component <component>...] [--notify/--no-notify]

# Edit an existing update: fix its text, time or affected components (no notifications are sent)
pngr pages incidents updates edit <incident-id> <update-id> --page-id <page-id> [--body <body>] [--posted-at <posted-at>] [--component <component>...] [--clear-components]

# Delete an update (an incident must keep at least one update)
pngr pages incidents updates delete <incident-id> <update-id> --page-id <page-id> [--confirm]
```

### `pngr pages incidents postmortem`
📝 Write and publish incident postmortems

```bash
# Show the postmortem of an incident (published text and pending draft)
pngr pages incidents postmortem get <incident-id> --page-id <page-id>

# Create or replace the postmortem draft (publish separately)
pngr pages incidents postmortem set <incident-id> --page-id <page-id> [--body <body>] [--file <file>] [--notify-subscribers/--no-notify-subscribers]

# Publish the current draft on the status page
pngr pages incidents postmortem publish <incident-id> --page-id <page-id> [--notify-subscribers/--no-notify-subscribers]
```

### `pngr pages passwords`
🔑 Manage passwords of password-protected status pages

```bash
# List page passwords with their hints, state and expiry (passwords themselves are never shown)
pngr pages passwords list --page-id <page-id>

# Add a password (enables password protection on the page; max 10 passwords)
pngr pages passwords add --page-id <page-id> [--password <password>] [--name <name>] [--hint <hint>] [--expires <expires>]

# Update a password's value, label, hint, state or expiry
pngr pages passwords update <password-id> --page-id <page-id> [--password <password>] [--name <name>] [--hint <hint>] [--active/--inactive] [--expires <expires>] [--no-expiry]

# Delete a password (removing the last one turns password protection off)
pngr pages passwords delete <password-id> --page-id <page-id> [--confirm]
```

### `pngr pages email-domain`
✉️  Send notifications from your own email domain

```bash
# Show the sender domain, its verification status and the DNS records to create
pngr pages email-domain show --page-id <page-id>

# Register the sender email's domain with the mail provider and print the DNS records to add
pngr pages email-domain setup --page-id <page-id> [--from-email <from-email>] [--from-name <from-name>]

# Check the DNS records with the mail provider and refresh the verification status
pngr pages email-domain verify --page-id <page-id>
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
# From command line options (waits for result by default)
pngr checks run custom --url https://example.com --type web

# Just queue without waiting for results
pngr checks run custom --url https://example.com --type web --no-wait

# From configuration file (waits for result by default)
pngr checks run custom --from-file check-config.json
pngr checks run custom --from-file check-config.yaml

# Combine file and command line (command line options override file values)
pngr checks run custom --from-file check-config.json --name "Override Name"
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

# Update a status page
pngr pages update page_123 --name "Updated Name" --description "New description"

# Make a page public
pngr pages update page_123 --public

# Update page timezone and language
pngr pages update page_123 --timezone "America/New_York" --language "en"

# Create an incident
pngr incidents create --name "Database Issues" --body "Investigating connectivity" --status investigating --impact major

# Update component status  
pngr pages components update comp_123 --page-id page_123 --status degraded_performance

# Get uptime for a specific component
pngr pages components uptime comp_123 --page-id page_123

# Get uptime for a specific component with date range
pngr pages components uptime comp_123 --page-id page_123 --start 2024-01-01 --end 2024-01-31

# Get uptime for all components on a page
pngr pages components uptime-bulk --page-id page_123

# Get uptime for all components with date range
pngr pages components uptime-bulk --page-id page_123 --start 2024-01-01 --end 2024-01-31

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