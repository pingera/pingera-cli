"""
Alert rules commands: when to fire an alert for a check and which channels to notify
"""

from typing import Any, Dict, List, Optional

import typer
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from .alert_common import (
    CONDITIONS,
    REGION_MODES,
    SEVERITIES,
    SEVERITY_STYLE,
    as_dict,
    as_list,
    channel_target,
    check_choice,
    human_seconds,
    load_file,
    parse_json_option,
    parse_seconds,
    raw_call,
    styled,
    text,
)
from .base import BaseCommand
from ..utils.time_utils import format_dt

RULE_FIELDS = ("name", "check_id", "enabled", "severity", "condition", "condition_parameters", "cooldown_period",
               "auto_resolve", "multi_region_mode", "multi_region_threshold", "channel_ids")
READ_ONLY_FIELDS = ("id", "created_at", "updated_at", "check_name", "channels")
CONDITION_HELP = ", ".join(CONDITIONS)


def describe_condition(condition: Any, params: Any) -> str:
    params = as_dict(params)
    if condition == "check_failed":
        return "Check fails"
    if condition == "check_timeout":
        return "Check times out"
    if condition == "check_degraded":
        return "Check is degraded"
    if condition == "consecutive_failures":
        return f"{text(params.get('count'), '3')} consecutive failures"
    if condition == "uptime_below_threshold":
        window = params.get("time_window", 3600)
        return f"Uptime below {text(params.get('threshold'), '95')}% over {human_seconds(window)}"
    return text(condition)


def describe_regions(mode: Any, threshold: Any) -> str:
    if mode == "all_regions":
        return "all regions fail"
    if mode == "majority":
        return "majority of regions fail"
    if mode == "specific_count":
        return f"at least {text(as_dict(threshold).get('count'))} regions fail"
    return "any region fails"


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _channel_ids(rule: Dict[str, Any]) -> List[str]:
    ids = rule.get("channel_ids")
    if isinstance(ids, list) and ids and all(isinstance(i, str) for i in ids):
        return ids
    return [c["id"] for c in as_list(rule.get("channels")) if isinstance(c, dict) and isinstance(c.get("id"), str)]


def _current_payload(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Writable fields of an existing rule (the API returns `channels` objects instead of `channel_ids`)."""
    checks = {
        "name": lambda v: isinstance(v, str) and v,
        "enabled": lambda v: isinstance(v, bool),
        "severity": lambda v: v in SEVERITIES,
        "condition": lambda v: v in CONDITIONS,
        "condition_parameters": lambda v: isinstance(v, dict),
        "cooldown_period": lambda v: _is_int(v) and v >= 0,
        "auto_resolve": lambda v: isinstance(v, bool),
        "multi_region_mode": lambda v: v in REGION_MODES,
        "multi_region_threshold": lambda v: isinstance(v, dict),
    }
    payload = {k: rule[k] for k, ok in checks.items() if k in rule and ok(rule[k])}
    ids = _channel_ids(rule)
    if ids:
        payload["channel_ids"] = ids
    return payload


def _file_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    unknown = sorted(set(data) - set(RULE_FIELDS) - set(READ_ONLY_FIELDS))
    if unknown:
        raise typer.BadParameter(
            f"unknown field(s) {', '.join(unknown)}; allowed: {', '.join(RULE_FIELDS)}", param_hint="--from-file"
        )
    payload = {k: data[k] for k in RULE_FIELDS if data.get(k) is not None}
    if "channel_ids" not in payload:
        ids = _channel_ids(data)
        if ids:
            payload["channel_ids"] = ids
    return payload


def build_rule(base: Dict[str, Any], file_data: Dict[str, Any], flags: Dict[str, Any], create: bool) -> Dict[str, Any]:
    """Merge existing rule (update), file values and command-line flags (flags win)."""
    payload = {**base, **file_data}

    for flag, field in (("name", "name"), ("check_id", "check_id"), ("severity", "severity"),
                        ("enabled", "enabled"), ("auto_resolve", "auto_resolve"), ("cooldown", "cooldown_period")):
        if flags.get(flag) is not None:
            payload[field] = flags[flag]
    if flags.get("channels"):
        payload["channel_ids"] = list(dict.fromkeys(flags["channels"]))

    condition = flags.get("condition")
    if condition is None:
        if flags.get("count") is not None:
            condition = "consecutive_failures"
        elif flags.get("threshold") is not None or flags.get("window") is not None:
            condition = "uptime_below_threshold"
    condition = condition or payload.get("condition") or ("check_failed" if create else None)

    if condition is not None:
        if condition == base.get("condition"):
            params = {**as_dict(base.get("condition_parameters"))}
        else:
            params = {}
        params.update(as_dict(file_data.get("condition_parameters")))
        params.update(flags.get("params") or {})
        if flags.get("count") is not None:
            params["count"] = flags["count"]
        if flags.get("threshold") is not None:
            params["threshold"] = flags["threshold"]
        if flags.get("window") is not None:
            params["time_window"] = flags["window"]
        payload["condition"] = condition
        payload["condition_parameters"] = {k: v for k, v in params.items() if v is not None}

    mode = flags.get("regions") or ("specific_count" if flags.get("regions_count") is not None else None)
    if mode:
        payload["multi_region_mode"] = mode
    if flags.get("regions_count") is not None:
        payload["multi_region_threshold"] = {"count": flags["regions_count"]}
    return payload


def validate_rule(payload: Dict[str, Any], flags: Dict[str, Any], create: bool, condition_touched: bool,
                  regions_touched: bool):
    """Mirror the backend's validation so mistakes fail fast with a usage error."""
    if create:
        missing = [opt for opt, field in (("--name", "name"), ("--check", "check_id"), ("--channel", "channel_ids"))
                   if not payload.get(field)]
        if missing:
            raise typer.BadParameter(f"missing {', '.join(missing)} (or set them in --from-file)")
    check_choice(payload.get("severity"), SEVERITIES, "--severity")
    check_choice(payload.get("condition"), CONDITIONS, "--condition")
    check_choice(payload.get("multi_region_mode"), REGION_MODES, "--regions")

    condition = payload.get("condition")
    if flags.get("count") is not None and condition != "consecutive_failures":
        raise typer.BadParameter("only applies to --condition consecutive_failures", param_hint="--count")
    for opt in ("threshold", "window"):
        if flags.get(opt) is not None and condition != "uptime_below_threshold":
            raise typer.BadParameter("only applies to --condition uptime_below_threshold", param_hint=f"--{opt}")

    if condition_touched:
        params = as_dict(payload.get("condition_parameters"))
        if condition == "consecutive_failures":
            count = params.get("count")
            if not _is_int(count) or count < 1:
                raise typer.BadParameter("consecutive_failures needs an integer --count >= 1", param_hint="--count")
        elif condition == "uptime_below_threshold":
            threshold = params.get("threshold")
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 < threshold < 100:
                raise typer.BadParameter("uptime_below_threshold needs --threshold between 0 and 100 (exclusive)",
                                         param_hint="--threshold")
    if regions_touched and payload.get("multi_region_mode") == "specific_count":
        count = as_dict(payload.get("multi_region_threshold")).get("count")
        if not _is_int(count) or count < 1:
            raise typer.BadParameter("specific_count mode needs --regions-count >= 1", param_hint="--regions-count")
    if flags.get("regions_count") is not None and payload.get("multi_region_mode") != "specific_count":
        raise typer.BadParameter("only applies to --regions specific_count", param_hint="--regions-count")


class AlertRulesCommand(BaseCommand):
    """Alert rules CRUD"""

    def __init__(self, output_format: Optional[str] = None):
        super().__init__(output_format)

    def _api(self):
        from pingera.api import AlertsApi
        return self.api(AlertsApi)

    def list_rules(self, check_id: Optional[str], enabled: Optional[bool]):
        try:
            data = raw_call(self._api(), "v1_alerts_rules_get")
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("list alert rules", e)

        rules = [r for r in as_list(data) if isinstance(r, dict)]
        if check_id:
            rules = [r for r in rules if r.get("check_id") == check_id]
        if enabled is not None:
            rules = [r for r in rules if r.get("enabled") is enabled]
        if self.machine_output:
            self.output_data(rules)
            return
        if not rules:
            self.display_info("No alert rules found. Create one with 'pngr alerts rules create'.")
            return

        table = Table(title="Alert rules", header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", max_width=30)
        table.add_column("Check", max_width=28)
        table.add_column("Trigger")
        table.add_column("Severity")
        table.add_column("Channels")
        table.add_column("Cooldown", justify="right")
        table.add_column("Enabled")
        for r in rules:
            channels = [c for c in as_list(r.get("channels")) if isinstance(c, dict)]
            names = [text(c.get("name"), text(c.get("id"))) for c in channels] or _channel_ids(r)
            table.add_row(
                text(r.get("id")),
                text(r.get("name")),
                text(r.get("check_name"), text(r.get("check_id"))),
                describe_condition(r.get("condition"), r.get("condition_parameters")),
                styled(r.get("severity"), SEVERITY_STYLE),
                ", ".join(names[:3]) + (f" (+{len(names) - 3})" if len(names) > 3 else "") or "-",
                human_seconds(r.get("cooldown_period")),
                "[green]yes[/green]" if r.get("enabled") is True else "[dim]no[/dim]",
            )
        self.console.print(table)
        self.console.print(f"[dim]{len(rules)} rule(s)[/dim]")

    def _get(self, rule_id: str) -> Dict[str, Any]:
        data = raw_call(self._api(), "v1_alerts_rules_rule_id_get", rule_id=rule_id)
        return as_dict(data)

    def get_rule(self, rule_id: str):
        try:
            rule = self._get(rule_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get alert rule", e)
        if self.machine_output:
            self.output_data(rule)
            return
        self.render_rule(rule)

    def render_rule(self, rule: Dict[str, Any]):
        check_name = text(rule.get("check_name"), "")
        enabled = rule.get("enabled") is not False
        lines = [
            f"[bold cyan]ID:[/bold cyan] {text(rule.get('id'))}",
            f"[bold cyan]Enabled:[/bold cyan] {'[green]yes[/green]' if enabled else '[yellow]no (paused)[/yellow]'}",
            f"[bold cyan]Check:[/bold cyan] {check_name + ' ' if check_name else ''}[dim]({text(rule.get('check_id'))})[/dim]",
            f"[bold cyan]Fires when:[/bold cyan] {describe_condition(rule.get('condition'), rule.get('condition_parameters'))}"
            f" [dim]({text(rule.get('condition'))})[/dim]",
            f"[bold cyan]Multi-region:[/bold cyan] {describe_regions(rule.get('multi_region_mode'), rule.get('multi_region_threshold'))}",
            f"[bold cyan]Severity:[/bold cyan] {styled(rule.get('severity'), SEVERITY_STYLE)}",
            f"[bold cyan]Cooldown:[/bold cyan] {human_seconds(rule.get('cooldown_period'))} between alerts",
            f"[bold cyan]Auto-resolve:[/bold cyan] {'yes, when the check recovers' if rule.get('auto_resolve') is not False else 'no'}",
            f"[bold cyan]Created:[/bold cyan] {format_dt(rule.get('created_at'))}   "
            f"[bold cyan]Updated:[/bold cyan] {format_dt(rule.get('updated_at'))}",
        ]
        self.console.print(Panel("\n".join(lines), title=f"📏 Alert rule: {text(rule.get('name'))}",
                                 border_style="cyan" if enabled else "yellow", padding=(1, 2)))

        channels = [c for c in as_list(rule.get("channels")) if isinstance(c, dict)]
        if channels:
            table = Table(title="Notifies", header_style="bold magenta")
            table.add_column("Channel ID", style="cyan")
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Target")
            table.add_column("Enabled")
            for c in channels:
                table.add_row(
                    text(c.get("id")), text(c.get("name")), text(c.get("type")),
                    channel_target(c.get("type"), c.get("configuration")),
                    "[green]yes[/green]" if c.get("enabled") is not False else "[dim]no[/dim]",
                )
            self.console.print(table)
        elif _channel_ids(rule):
            self.console.print(f"[bold cyan]Notifies channels:[/bold cyan] {', '.join(_channel_ids(rule))}")

    def _done(self, rule: Dict[str, Any], title: str):
        if self.machine_output:
            self.output_data(rule)
            return
        channels = len(_channel_ids(rule))
        self.display_success(
            f"[bold cyan]ID:[/bold cyan] {text(rule.get('id'))}\n"
            f"[bold cyan]Name:[/bold cyan] {text(rule.get('name'))}\n"
            f"[bold cyan]Check:[/bold cyan] {text(rule.get('check_name'), text(rule.get('check_id')))}\n"
            f"[bold cyan]Fires when:[/bold cyan] {describe_condition(rule.get('condition'), rule.get('condition_parameters'))}\n"
            f"[bold cyan]Notifies:[/bold cyan] {channels} channel(s)\n"
            f"[bold cyan]Enabled:[/bold cyan] {'yes' if rule.get('enabled') is not False else 'no'}",
            title,
        )

    def create_rule(self, file_path: Optional[str], flags: Dict[str, Any]):
        file_data = _file_payload(load_file(file_path))
        payload = build_rule({}, file_data, flags, create=True)
        validate_rule(payload, flags, create=True, condition_touched=True, regions_touched=True)
        try:
            rule = raw_call(self._api(), "v1_alerts_rules_post", alert_rule=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("create alert rule", e)
        self._done(as_dict(rule), "✅ Alert rule created")

    def update_rule(self, rule_id: str, file_path: Optional[str], flags: Dict[str, Any]):
        file_data = _file_payload(load_file(file_path))
        if not file_data and not any(v not in (None, [], {}) for v in flags.values()):
            raise typer.BadParameter("nothing to update; pass at least one option or --from-file")
        new_check = file_data.pop("check_id", None)
        try:
            current = self._get(rule_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get alert rule", e)
        if new_check and new_check != current.get("check_id"):
            self.display_warning("The check of an existing rule can't be changed; 'check_id' was ignored. "
                                 "Create a new rule for the other check instead.")

        condition_keys = ("condition", "count", "threshold", "window", "params")
        condition_touched = any(flags.get(k) is not None for k in condition_keys) or \
            any(k in file_data for k in ("condition", "condition_parameters"))
        regions_touched = flags.get("regions") is not None or flags.get("regions_count") is not None or \
            any(k in file_data for k in ("multi_region_mode", "multi_region_threshold"))

        base = _current_payload(current)
        payload = build_rule(base, file_data, flags, create=False)
        validate_rule(payload, flags, create=False, condition_touched=condition_touched, regions_touched=regions_touched)
        self._put(rule_id, payload, "update alert rule", "✅ Alert rule updated")

    def _put(self, rule_id: str, payload: Dict[str, Any], action: str, title: str):
        # The full rule is sent: the SDK update model fills unset fields with defaults (enabled=True, cooldown 300...)
        try:
            rule = raw_call(self._api(), "v1_alerts_rules_rule_id_put", rule_id=rule_id, alert_rule1=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail(action, e)
        self._done(as_dict(rule), title)

    def set_enabled(self, rule_id: str, enabled: bool):
        action = "enable" if enabled else "disable"
        try:
            current = self._get(rule_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail(f"{action} alert rule", e)
        payload = {**_current_payload(current), "enabled": enabled}
        self._put(rule_id, payload, f"{action} alert rule",
                  "✅ Alert rule enabled" if enabled else "⏸️ Alert rule disabled")

    def delete_rule(self, rule_id: str, confirm: bool):
        if not confirm and not Confirm.ask(f"Delete alert rule {rule_id}? Its alert history is deleted too.",
                                           console=self._status_console):
            self._status_console.print("[yellow]Operation cancelled.[/yellow]")
            return
        try:
            self._api().v1_alerts_rules_rule_id_delete(rule_id=rule_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("delete alert rule", e)
        if self.machine_output:
            self.output_data({"deleted": True, "id": rule_id})
        else:
            self.display_success(f"Alert rule {rule_id} deleted.", "✅ Alert rule deleted")


app = typer.Typer(name="rules", help="📏 Manage alert rules (when to alert and whom to notify)", no_args_is_help=True)


def _rule_flags(name, check_id, condition, count, threshold, window, params, severity, channels, cooldown,
                auto_resolve, regions, regions_count, enabled) -> Dict[str, Any]:
    check_choice(condition, CONDITIONS, "--condition")
    check_choice(severity, SEVERITIES, "--severity")
    check_choice(regions, REGION_MODES, "--regions")
    if count is not None and threshold is not None:
        raise typer.BadParameter("--count (consecutive_failures) and --threshold (uptime_below_threshold) "
                                 "are mutually exclusive")
    return {
        "name": name, "check_id": check_id, "condition": condition, "count": count, "threshold": threshold,
        "window": parse_seconds(window, "--window"), "params": parse_json_option(params, "--params"),
        "severity": severity, "channels": channels or [], "cooldown": parse_seconds(cooldown, "--cooldown"),
        "auto_resolve": auto_resolve, "regions": regions, "regions_count": regions_count, "enabled": enabled,
    }


_FILE_HELP = ("JSON/YAML file (or URL) with rule fields: " + ", ".join(RULE_FIELDS) +
              ". Output of 'rules get -o json' works too. Command-line options override file values")


@app.command("list")
def list_rules(
    check_id: Optional[str] = typer.Option(None, "--check", "-c", help="Only rules for this check ID"),
    enabled: Optional[bool] = typer.Option(None, "--enabled/--disabled", help="Only enabled / disabled rules"),
):
    """List alert rules"""
    from ..utils.config import get_output_format
    AlertRulesCommand(get_output_format()).list_rules(check_id, enabled)


@app.command("get")
def get_rule(rule_id: str = typer.Argument(..., help="Alert rule ID")):
    """Show a rule: its check, trigger condition, multi-region mode and notified channels"""
    from ..utils.config import get_output_format
    AlertRulesCommand(get_output_format()).get_rule(rule_id)


@app.command("create")
def create_rule(
    from_file: Optional[str] = typer.Option(None, "--from-file", "-f", help=_FILE_HELP),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Rule name (max 100 chars)"),
    check_id: Optional[str] = typer.Option(None, "--check", "-c", help="Check ID the rule watches (one check per rule)"),
    condition: Optional[str] = typer.Option(
        None, "--condition", help=f"Trigger: {CONDITION_HELP}. Default: check_failed, or inferred from --count/--threshold"),
    count: Optional[int] = typer.Option(None, "--count", min=1, help="Failures in a row (consecutive_failures)"),
    threshold: Optional[float] = typer.Option(None, "--threshold", help="Uptime % below which to alert, 0-100 (uptime_below_threshold)"),
    window: Optional[str] = typer.Option(None, "--window", help="Uptime window, e.g. 30m, 1h, 1d (uptime_below_threshold; default 1h)"),
    params: Optional[str] = typer.Option(None, "--params", help="Raw condition_parameters JSON, e.g. '{\"count\": 3}'"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="low, medium (default), high or critical"),
    channels: Optional[List[str]] = typer.Option(None, "--channel", help="Channel ID to notify (repeat for several)"),
    cooldown: Optional[str] = typer.Option(None, "--cooldown", help="Minimum time between alerts, e.g. 300, 10m, 1h (default 5m)"),
    auto_resolve: Optional[bool] = typer.Option(None, "--auto-resolve/--no-auto-resolve", help="Resolve automatically when the check recovers (default: yes)"),
    regions: Optional[str] = typer.Option(None, "--regions", help="Multi-region mode: any_region (default), all_regions, majority, specific_count"),
    regions_count: Optional[int] = typer.Option(None, "--regions-count", min=1, help="Failing regions needed (implies --regions specific_count)"),
    enabled: Optional[bool] = typer.Option(None, "--enabled/--disabled", help="Create enabled (default) or paused"),
):
    """Create an alert rule for a check

    Example: pngr alerts rules create -n "API down" -c chk123 --count 3 --channel chn1 --severity high
    """
    from ..utils.config import get_output_format
    flags = _rule_flags(name, check_id, condition, count, threshold, window, params, severity, channels, cooldown,
                        auto_resolve, regions, regions_count, enabled)
    AlertRulesCommand(get_output_format()).create_rule(from_file, flags)


@app.command("update")
def update_rule(
    rule_id: str = typer.Argument(..., help="Alert rule ID"),
    from_file: Optional[str] = typer.Option(None, "--from-file", "-f", help=_FILE_HELP),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name"),
    condition: Optional[str] = typer.Option(None, "--condition", help=f"New trigger: {CONDITION_HELP}"),
    count: Optional[int] = typer.Option(None, "--count", min=1, help="Failures in a row (implies consecutive_failures)"),
    threshold: Optional[float] = typer.Option(None, "--threshold", help="Uptime % threshold, 0-100 (implies uptime_below_threshold)"),
    window: Optional[str] = typer.Option(None, "--window", help="Uptime window, e.g. 1h (uptime_below_threshold)"),
    params: Optional[str] = typer.Option(None, "--params", help="condition_parameters JSON merged into the current ones"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="low, medium, high or critical"),
    channels: Optional[List[str]] = typer.Option(None, "--channel", help="Replace notified channels (repeat for several)"),
    cooldown: Optional[str] = typer.Option(None, "--cooldown", help="Minimum time between alerts, e.g. 300, 10m, 1h"),
    auto_resolve: Optional[bool] = typer.Option(None, "--auto-resolve/--no-auto-resolve", help="Resolve automatically when the check recovers"),
    regions: Optional[str] = typer.Option(None, "--regions", help="Multi-region mode: any_region, all_regions, majority, specific_count"),
    regions_count: Optional[int] = typer.Option(None, "--regions-count", min=1, help="Failing regions needed (implies specific_count)"),
    enabled: Optional[bool] = typer.Option(None, "--enabled/--disabled", help="Enable or pause the rule"),
):
    """Update an alert rule (only the given fields change; the check can't be changed)"""
    from ..utils.config import get_output_format
    flags = _rule_flags(name, None, condition, count, threshold, window, params, severity, channels, cooldown,
                        auto_resolve, regions, regions_count, enabled)
    AlertRulesCommand(get_output_format()).update_rule(rule_id, from_file, flags)


@app.command("enable")
def enable_rule(rule_id: str = typer.Argument(..., help="Alert rule ID")):
    """Enable an alert rule"""
    from ..utils.config import get_output_format
    AlertRulesCommand(get_output_format()).set_enabled(rule_id, True)


@app.command("disable")
def disable_rule(rule_id: str = typer.Argument(..., help="Alert rule ID")):
    """Disable (pause) an alert rule without deleting it"""
    from ..utils.config import get_output_format
    AlertRulesCommand(get_output_format()).set_enabled(rule_id, False)


@app.command("delete")
def delete_rule(
    rule_id: str = typer.Argument(..., help="Alert rule ID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip the confirmation prompt"),
):
    """Delete an alert rule and its alert history"""
    from ..utils.config import get_output_format
    AlertRulesCommand(get_output_format()).delete_rule(rule_id, confirm)
