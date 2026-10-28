"""
Alert channels commands: where alert notifications are delivered (email, webhook, Telegram, MAX, SMS, status page)
"""

from typing import Any, Dict, List, Optional

import typer
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from .alert_common import (
    CHANNEL_TYPES,
    E164,
    TESTABLE_CHANNEL_TYPES,
    WEBHOOK_METHODS,
    as_dict,
    channel_target,
    check_choice,
    dump,
    load_file,
    mask_config,
    mask_url,
    parse_json_option,
    text,
)
from .base import BaseCommand
from ..utils.time_utils import format_dt

CHANNEL_FIELDS = ("name", "type", "enabled", "configuration")
READ_ONLY_FIELDS = ("id", "created_at", "updated_at", "last_used_at")

# config flag -> (option name, channel types it applies to)
CONFIG_FLAGS = {
    "emails": ("--email", ("email",)),
    "url": ("--url", ("webhook",)),
    "method": ("--method", ("webhook",)),
    "headers": ("--header", ("webhook",)),
    "timeout": ("--timeout", ("webhook",)),
    "chat_id": ("--chat-id", ("telegram", "max")),
    "phones": ("--phone", ("sms",)),
    "page_id": ("--page-id", ("statuspage",)),
    "component_id": ("--component-id", ("statuspage",)),
}


def _given(flags: Dict[str, Any]) -> List[str]:
    return [k for k in CONFIG_FLAGS if flags.get(k) not in (None, [])]


def infer_type(flags: Dict[str, Any]) -> Optional[str]:
    candidates = None
    for key in _given(flags):
        types = set(CONFIG_FLAGS[key][1])
        candidates = types if candidates is None else candidates & types
    if candidates and len(candidates) == 1:
        return next(iter(candidates))
    return None


def _parse_headers(values: List[str]) -> Dict[str, Optional[str]]:
    headers: Dict[str, Optional[str]] = {}
    for item in values:
        name, sep, value = item.partition(":")
        if not sep or not name.strip():
            raise typer.BadParameter(f"'{item}' is not 'Name: value'", param_hint="--header")
        headers[name.strip()] = value.strip() or None
    return headers


def build_config(base: Dict[str, Any], config_json: Optional[Dict[str, Any]], flags: Dict[str, Any],
                 channel_type: Optional[str]) -> Dict[str, Any]:
    """Merge configuration: base < --config (null removes a key) < per-type flags."""
    for key in _given(flags):
        option, types = CONFIG_FLAGS[key]
        if channel_type not in types:
            raise typer.BadParameter(f"only valid for {'/'.join(types)} channels (this one is {channel_type})",
                                     param_hint=option)
    config = dict(base)
    for key, value in (config_json or {}).items():
        if value is None:
            config.pop(key, None)
        else:
            config[key] = value
    if flags.get("emails"):
        config["recipients"] = list(dict.fromkeys(flags["emails"]))
    if flags.get("url"):
        config["url"] = flags["url"]
    if flags.get("method"):
        config["method"] = flags["method"].upper()
    if flags.get("headers"):
        headers = {**as_dict(config.get("headers"))}
        for name, value in _parse_headers(flags["headers"]).items():
            if value is None:
                headers.pop(name, None)
            else:
                headers[name] = value
        config["headers"] = headers
    if flags.get("timeout") is not None:
        config["timeout"] = flags["timeout"]
    if flags.get("chat_id"):
        config["chat_id"] = flags["chat_id"]
    if flags.get("phones"):
        config["phone_numbers"] = list(dict.fromkeys(flags["phones"]))
    if flags.get("page_id"):
        config["page_id"] = flags["page_id"]
    if flags.get("component_id"):
        config["component_id"] = flags["component_id"]
    return config


def validate_config(channel_type: str, config: Dict[str, Any]):
    """Same rules as the backend, so mistakes are usage errors instead of HTTP 422s."""
    def bad(message: str, option: str):
        raise typer.BadParameter(message, param_hint=option)

    if channel_type == "email":
        recipients = config.get("recipients")
        if not isinstance(recipients, list) or not recipients:
            bad("email channels need at least one recipient", "--email")
        for r in recipients:
            if not isinstance(r, str) or "@" not in r:
                bad(f"'{r}' is not an email address", "--email")
    elif channel_type == "webhook":
        url = config.get("url")
        if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
            bad("webhook channels need an http(s) --url", "--url")
        method = config.get("method")
        if method is not None and str(method).upper() not in WEBHOOK_METHODS:
            bad(f"must be one of {', '.join(WEBHOOK_METHODS)}", "--method")
        if "headers" in config and not isinstance(config["headers"], dict):
            bad("headers must be a JSON object", "--config")
    elif channel_type in ("telegram", "max"):
        if not config.get("chat_id"):
            bad(f"{channel_type} channels need --chat-id", "--chat-id")
    elif channel_type == "sms":
        phones = config.get("phone_numbers")
        if not isinstance(phones, list) or not phones:
            bad("sms channels need at least one --phone", "--phone")
        for p in phones:
            if not isinstance(p, str) or not E164.match(p):
                bad(f"'{p}' is not in E.164 format (e.g. +79998887766)", "--phone")
    elif channel_type == "statuspage":
        if not config.get("page_id"):
            bad("statuspage channels need --page-id", "--page-id")


def _file_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    unknown = sorted(set(data) - set(CHANNEL_FIELDS) - set(READ_ONLY_FIELDS))
    if unknown:
        raise typer.BadParameter(
            f"unknown field(s) {', '.join(unknown)}; allowed: {', '.join(CHANNEL_FIELDS)}", param_hint="--from-file"
        )
    payload = {k: data[k] for k in CHANNEL_FIELDS if data.get(k) is not None}
    if "configuration" in payload and not isinstance(payload["configuration"], dict):
        raise typer.BadParameter("'configuration' must be an object", param_hint="--from-file")
    return payload


def _config_lines(config: Dict[str, Any]) -> List[str]:
    lines = []
    for key, value in mask_config(config).items():
        if isinstance(value, list):
            value = ", ".join(text(v) for v in value) or "-"
        elif isinstance(value, dict):
            value = ", ".join(f"{k}={text(v)}" for k, v in value.items()) or "-"
        else:
            value = text(value)
        lines.append(f"  [cyan]{key}:[/cyan] {value}")
    return lines


class AlertChannelsCommand(BaseCommand):
    """Alert channels CRUD and test notifications"""

    def __init__(self, output_format: Optional[str] = None):
        super().__init__(output_format)

    def _api(self):
        from pingera.api import AlertsApi
        return self.api(AlertsApi)

    def list_channels(self, channel_type: Optional[str]):
        try:
            channels = self._api().v1_alerts_channels_get() or []
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("list alert channels", e)

        if channel_type:
            channels = [c for c in channels if c.type == channel_type]
        if self.machine_output:
            self.output_data(dump(channels))
            return
        if not channels:
            self.display_info("No alert channels found. Create one with 'pngr alerts channels create'.")
            return

        table = Table(title="Alert channels", header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", max_width=30)
        table.add_column("Type")
        table.add_column("Target", max_width=50)
        table.add_column("Enabled")
        table.add_column("Last used (UTC)")
        for c in channels:
            table.add_row(
                text(c.id), text(c.name), text(c.type), channel_target(c.type, c.configuration),
                "[green]yes[/green]" if c.enabled is not False else "[dim]no[/dim]",
                format_dt(c.last_used_at) if c.last_used_at else "never",
            )
        self.console.print(table)
        self.console.print(f"[dim]{len(channels)} channel(s) • secrets and webhook URL paths are masked; "
                           f"use -o json for the full configuration[/dim]")

    def _get(self, channel_id: str):
        return self._api().v1_alerts_channels_channel_id_get(channel_id=channel_id)

    def get_channel(self, channel_id: str):
        try:
            channel = self._get(channel_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get alert channel", e)
        if self.machine_output:
            self.output_data(dump(channel))
            return
        enabled = channel.enabled is not False
        lines = [
            f"[bold cyan]ID:[/bold cyan] {text(channel.id)}",
            f"[bold cyan]Type:[/bold cyan] {text(channel.type)}",
            f"[bold cyan]Enabled:[/bold cyan] {'[green]yes[/green]' if enabled else '[yellow]no[/yellow]'}",
            f"[bold cyan]Delivers to:[/bold cyan] {channel_target(channel.type, channel.configuration)}",
            f"[bold cyan]Last used:[/bold cyan] {format_dt(channel.last_used_at) if channel.last_used_at else 'never'}",
            f"[bold cyan]Created:[/bold cyan] {format_dt(channel.created_at)}   "
            f"[bold cyan]Updated:[/bold cyan] {format_dt(channel.updated_at)}",
            "[bold cyan]Configuration:[/bold cyan] [dim](secrets masked)[/dim]",
            *(_config_lines(as_dict(channel.configuration)) or ["  -"]),
        ]
        self.console.print(Panel("\n".join(lines), title=f"📣 Alert channel: {text(channel.name)}",
                                 border_style="cyan" if enabled else "yellow", padding=(1, 2)))

    def _done(self, channel, title: str):
        if self.machine_output:
            self.output_data(dump(channel))
            return
        self.display_success(
            f"[bold cyan]ID:[/bold cyan] {text(channel.id)}\n"
            f"[bold cyan]Name:[/bold cyan] {text(channel.name)}\n"
            f"[bold cyan]Type:[/bold cyan] {text(channel.type)}\n"
            f"[bold cyan]Delivers to:[/bold cyan] {channel_target(channel.type, channel.configuration)}\n"
            f"[bold cyan]Enabled:[/bold cyan] {'yes' if channel.enabled is not False else 'no'}",
            title,
        )

    def create_channel(self, file_path: Optional[str], name: Optional[str], channel_type: Optional[str],
                       enabled: Optional[bool], config_json: Optional[str], flags: Dict[str, Any], test_first: bool):
        payload = _file_payload(load_file(file_path))
        config_json = parse_json_option(config_json, "--config")
        if name:
            payload["name"] = name
        if enabled is not None:
            payload["enabled"] = enabled
        channel_type = channel_type or payload.get("type") or infer_type(flags)
        if not channel_type:
            raise typer.BadParameter(f"can't tell the channel type; pass one of: {', '.join(CHANNEL_TYPES)}",
                                     param_hint="--type")
        check_choice(channel_type, CHANNEL_TYPES, "--type")
        payload["type"] = channel_type
        if not payload.get("name"):
            raise typer.BadParameter("missing channel name (or set 'name' in --from-file)", param_hint="--name")
        payload["configuration"] = build_config(as_dict(payload.get("configuration")), config_json, flags, channel_type)
        validate_config(channel_type, payload["configuration"])
        if test_first:
            self._require_testable(channel_type)

        try:
            api = self._api()
            if test_first:
                result = api.v1_alerts_channels_test_post(alert_channel_test_request=payload)
                if result.success is not True:
                    self._render_test(result, payload.get("name"), quiet_success=True)
                    self.display_error("Test notification failed, channel was not created.")
                    raise typer.Exit(1)
                self._status_console.print("[green]✓ Test notification delivered[/green]")
            channel = api.v1_alerts_channels_post(alert_channel=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("create alert channel", e)
        self._done(channel, "✅ Alert channel created")

    def update_channel(self, channel_id: str, file_path: Optional[str], name: Optional[str], enabled: Optional[bool],
                       config_json: Optional[str], flags: Dict[str, Any]):
        file_data = _file_payload(load_file(file_path))
        config_json = parse_json_option(config_json, "--config")
        if not file_data and name is None and enabled is None and config_json is None and not _given(flags):
            raise typer.BadParameter("nothing to update; pass at least one option or --from-file")
        try:
            current = self._get(channel_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get alert channel", e)

        channel_type = current.type
        if file_data.get("type") not in (None, channel_type):
            raise typer.BadParameter(f"the type of a channel can't be changed ({channel_type}); create a new channel",
                                     param_hint="--from-file")
        payload = {"name": current.name, "type": channel_type,
                   "enabled": current.enabled if isinstance(current.enabled, bool) else True}
        payload.update({k: v for k, v in file_data.items() if k in ("name", "enabled")})
        if name is not None:
            payload["name"] = name
        if enabled is not None:
            payload["enabled"] = enabled
        base_config = {**as_dict(current.configuration), **as_dict(file_data.get("configuration"))}
        payload["configuration"] = build_config(base_config, config_json, flags, channel_type)
        if config_json is not None or _given(flags) or "configuration" in file_data:
            validate_config(channel_type, payload["configuration"])

        # The whole channel is sent: the SDK update model would otherwise reset `enabled` to true
        try:
            channel = self._api().v1_alerts_channels_channel_id_put(channel_id=channel_id, alert_channel1=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("update alert channel", e)
        self._done(channel, "✅ Alert channel updated")

    def delete_channel(self, channel_id: str, confirm: bool):
        if not confirm and not Confirm.ask(f"Delete alert channel {channel_id}?", console=self._status_console):
            self._status_console.print("[yellow]Operation cancelled.[/yellow]")
            return
        try:
            self._api().v1_alerts_channels_channel_id_delete(channel_id=channel_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("delete alert channel (channels used by alert rules can't be deleted)", e)
        if self.machine_output:
            self.output_data({"deleted": True, "id": channel_id})
        else:
            self.display_success(f"Alert channel {channel_id} deleted.", "✅ Alert channel deleted")

    @staticmethod
    def _require_testable(channel_type: str):
        if channel_type not in TESTABLE_CHANNEL_TYPES:
            raise typer.BadParameter(
                f"test notifications are supported for {', '.join(TESTABLE_CHANNEL_TYPES)} channels only",
                param_hint="--type",
            )

    def test_channel(self, channel_id: Optional[str], name: Optional[str], channel_type: Optional[str],
                     config_json: Optional[str], flags: Dict[str, Any]):
        payload = None
        if channel_id:
            if channel_type or config_json or name or _given(flags):
                raise typer.BadParameter("pass either a saved CHANNEL_ID or an unsaved configuration "
                                         "(--type and config options), not both")
        else:
            config_json = parse_json_option(config_json, "--config")
            channel_type = channel_type or infer_type(flags)
            if not channel_type:
                raise typer.BadParameter("pass a saved CHANNEL_ID, or --type plus its configuration options",
                                         param_hint="--type")
            check_choice(channel_type, CHANNEL_TYPES, "--type")
            self._require_testable(channel_type)
            config = build_config({}, config_json, flags, channel_type)
            validate_config(channel_type, config)
            payload = {"type": channel_type, "configuration": config}
            if name:
                payload["name"] = name

        try:
            api = self._api()
            if payload is None:
                result = api.v1_alerts_channels_channel_id_test_post(channel_id=channel_id)
            else:
                result = api.v1_alerts_channels_test_post(alert_channel_test_request=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("send test notification", e)

        if self.machine_output:
            self.output_data(dump(result))
        else:
            self._render_test(result, channel_id or name or f"unsaved {channel_type} channel")
        if result.success is not True:
            raise typer.Exit(1)

    def _render_test(self, result, label: Optional[str], quiet_success: bool = False):
        out = self._status_console if quiet_success else self.console
        if result.success is True:
            out.print(Panel(f"Test notification delivered via {text(label)}.", title="✅ Test passed",
                            border_style="green", padding=(1, 2)))
        else:
            out.print(Panel(f"[red]{text(result.error, 'Delivery failed')}[/red]", title="❌ Test failed",
                            border_style="red", padding=(1, 2)))
        deliveries = [d for d in (result.results or []) if d is not None]
        if deliveries:
            table = Table(title="Deliveries", header_style="bold magenta")
            table.add_column("Recipient")
            table.add_column("Result")
            table.add_column("Error", max_width=60)
            for d in deliveries:
                recipient = d.recipient
                if isinstance(recipient, str) and recipient.lower().startswith(("http://", "https://")):
                    recipient = mask_url(recipient)
                table.add_row(text(recipient), "[green]delivered[/green]" if d.success is True else "[red]failed[/red]",
                              text(d.error, ""))
            out.print(table)


app = typer.Typer(name="channels", help="📣 Manage alert notification channels", no_args_is_help=True)

_TYPE_HELP = "Channel type: " + ", ".join(CHANNEL_TYPES) + " (inferred from --email/--url/--phone/--page-id when omitted)"
_CONFIG_HELP = "Configuration JSON merged with the options below; a null value removes a key"


def _config_flags(emails, url, method, headers, timeout, chat_id, phones, page_id, component_id) -> Dict[str, Any]:
    if method is not None and method.upper() not in WEBHOOK_METHODS:
        raise typer.BadParameter(f"must be one of {', '.join(WEBHOOK_METHODS)}", param_hint="--method")
    return {"emails": emails or [], "url": url, "method": method, "headers": headers or [], "timeout": timeout,
            "chat_id": chat_id, "phones": phones or [], "page_id": page_id, "component_id": component_id}


def _opt_email():
    return typer.Option(None, "--email", help="[email] Recipient address (repeat for several)")


def _opt_url():
    return typer.Option(None, "--url", help="[webhook] URL to call")


def _opt_method():
    return typer.Option(None, "--method", help="[webhook] HTTP method: POST (default), PUT or PATCH")


def _opt_header():
    return typer.Option(None, "--header", "-H", help="[webhook] Extra header 'Name: value' (repeatable; 'Name:' removes)")


def _opt_timeout():
    return typer.Option(None, "--timeout", min=1, max=300, help="[webhook] Request timeout in seconds (default 30)")


def _opt_chat_id():
    return typer.Option(None, "--chat-id", help="[telegram, max] Chat ID linked to the Pingera bot")


def _opt_phone():
    return typer.Option(None, "--phone", help="[sms] Phone number in E.164 format, e.g. +79998887766 (repeatable)")


def _opt_page_id():
    return typer.Option(None, "--page-id", help="[statuspage] Status page ID")


def _opt_component_id():
    return typer.Option(None, "--component-id", help="[statuspage] Component ID whose status follows the alerts")


@app.command("list")
def list_channels(
    channel_type: Optional[str] = typer.Option(None, "--type", "-t", help="Only channels of this type: " + ", ".join(CHANNEL_TYPES)),
):
    """List alert channels (secrets masked)"""
    from ..utils.config import get_output_format
    check_choice(channel_type, CHANNEL_TYPES, "--type")
    AlertChannelsCommand(get_output_format()).list_channels(channel_type)


@app.command("get")
def get_channel(channel_id: str = typer.Argument(..., help="Alert channel ID")):
    """Show an alert channel and its configuration (secrets masked)"""
    from ..utils.config import get_output_format
    AlertChannelsCommand(get_output_format()).get_channel(channel_id)


@app.command("create")
def create_channel(
    from_file: Optional[str] = typer.Option(None, "--from-file", "-f", help="JSON/YAML file (or URL) with name, type, enabled, configuration; options override it"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Channel name (max 100 chars)"),
    channel_type: Optional[str] = typer.Option(None, "--type", "-t", help=_TYPE_HELP),
    emails: Optional[List[str]] = _opt_email(),
    url: Optional[str] = _opt_url(),
    method: Optional[str] = _opt_method(),
    headers: Optional[List[str]] = _opt_header(),
    timeout: Optional[int] = _opt_timeout(),
    chat_id: Optional[str] = _opt_chat_id(),
    phones: Optional[List[str]] = _opt_phone(),
    page_id: Optional[str] = _opt_page_id(),
    component_id: Optional[str] = _opt_component_id(),
    config: Optional[str] = typer.Option(None, "--config", help=_CONFIG_HELP),
    enabled: Optional[bool] = typer.Option(None, "--enabled/--disabled", help="Create enabled (default) or disabled"),
    test_first: bool = typer.Option(False, "--test", help="Send a test notification first and only create the channel if it is delivered (email, webhook, telegram, max)"),
):
    """Create an alert channel

    Examples: pngr alerts channels create -n Ops --email ops@example.com --email oncall@example.com
              pngr alerts channels create -n Hook --url https://example.com/hook -H 'Authorization: Bearer x' --test
    """
    from ..utils.config import get_output_format
    flags = _config_flags(emails, url, method, headers, timeout, chat_id, phones, page_id, component_id)
    AlertChannelsCommand(get_output_format()).create_channel(from_file, name, channel_type, enabled, config, flags,
                                                             test_first)


@app.command("update")
def update_channel(
    channel_id: str = typer.Argument(..., help="Alert channel ID"),
    from_file: Optional[str] = typer.Option(None, "--from-file", "-f", help="JSON/YAML file (or URL) with name, enabled, configuration (merged); options override it"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name"),
    emails: Optional[List[str]] = typer.Option(None, "--email", help="[email] Replace recipients (repeatable)"),
    url: Optional[str] = _opt_url(),
    method: Optional[str] = _opt_method(),
    headers: Optional[List[str]] = _opt_header(),
    timeout: Optional[int] = _opt_timeout(),
    chat_id: Optional[str] = _opt_chat_id(),
    phones: Optional[List[str]] = typer.Option(None, "--phone", help="[sms] Replace phone numbers, E.164 (repeatable)"),
    page_id: Optional[str] = _opt_page_id(),
    component_id: Optional[str] = _opt_component_id(),
    config: Optional[str] = typer.Option(None, "--config", help=_CONFIG_HELP + " (merged into the current configuration)"),
    enabled: Optional[bool] = typer.Option(None, "--enabled/--disabled", help="Enable or disable the channel"),
):
    """Update an alert channel (only the given fields change; the type can't be changed)"""
    from ..utils.config import get_output_format
    flags = _config_flags(emails, url, method, headers, timeout, chat_id, phones, page_id, component_id)
    AlertChannelsCommand(get_output_format()).update_channel(channel_id, from_file, name, enabled, config, flags)


@app.command("delete")
def delete_channel(
    channel_id: str = typer.Argument(..., help="Alert channel ID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip the confirmation prompt"),
):
    """Delete an alert channel (it must not be used by any alert rule)"""
    from ..utils.config import get_output_format
    AlertChannelsCommand(get_output_format()).delete_channel(channel_id, confirm)


@app.command("test")
def test_channel(
    channel_id: Optional[str] = typer.Argument(None, help="Saved channel ID; omit to test an unsaved configuration"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Channel name shown in the test message (unsaved config)"),
    channel_type: Optional[str] = typer.Option(None, "--type", "-t", help="Type of the unsaved configuration: " + ", ".join(TESTABLE_CHANNEL_TYPES)),
    emails: Optional[List[str]] = _opt_email(),
    url: Optional[str] = _opt_url(),
    method: Optional[str] = _opt_method(),
    headers: Optional[List[str]] = _opt_header(),
    timeout: Optional[int] = _opt_timeout(),
    chat_id: Optional[str] = _opt_chat_id(),
    config: Optional[str] = typer.Option(None, "--config", help="Configuration JSON of the unsaved channel"),
):
    """Send a test notification through a saved channel, or through an unsaved configuration

    Exits with status 1 if the notification was not delivered.
    Examples: pngr alerts channels test chn123
              pngr alerts channels test --url https://example.com/hook
              pngr alerts channels test --type telegram --chat-id 123456
    """
    from ..utils.config import get_output_format
    flags = _config_flags(emails, url, method, headers, timeout, chat_id, None, None, None)
    AlertChannelsCommand(get_output_format()).test_channel(channel_id, name, channel_type, config, flags)
