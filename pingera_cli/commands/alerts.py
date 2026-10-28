"""
Alerts commands: fired alerts (list/get/ack/resolve/notifications/stats) plus the rules and channels sub-groups
"""

from datetime import datetime
from typing import Any, List, Optional, Tuple

import typer
from rich.panel import Panel
from rich.table import Table

from .alert_channels import app as channels_app
from .alert_common import (
    ALERT_STATUSES,
    SEVERITIES,
    SEVERITY_STYLE,
    STATUS_STYLE,
    as_dict,
    as_list,
    check_choice,
    pagination_line,
    parse_dt,
    styled,
    text,
)
from .alert_rules import app as rules_app
from .base import BaseCommand, to_plain
from ..utils.time_utils import format_dt, format_duration, parse_time_arg

SCAN_PAGE_SIZE = 100
SCAN_MAX_PAGES = 20


def _duration(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return format_duration(value)
    return "-"


class AlertsCommand(BaseCommand):
    """Fired alerts: list, inspect, acknowledge, resolve"""

    def __init__(self, output_format: Optional[str] = None):
        super().__init__(output_format)

    def _api(self):
        from pingera.api import AlertsApi
        return self.api(AlertsApi)

    def list_alerts(self, status: Optional[str], check_id: Optional[str], severity: Optional[str],
                    start: Optional[str], end: Optional[str], page: int, per_page: int):
        start_dt = parse_time_arg(start, "--from")
        end_dt = parse_time_arg(end, "--to")
        filters = {"status": status, "check_id": check_id, "severity": severity}
        try:
            api = self._api()
            if start_dt or end_dt:
                alerts, scanned, truncated = self._scan(api, filters, start_dt, end_dt)
                pagination = None
            else:
                data = api.v1_alerts_get(**filters, page=page, per_page=per_page)
                alerts, pagination, scanned, truncated = data.alerts or [], data.pagination, 0, False
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("list alerts", e)

        if self.machine_output:
            result = {"alerts": to_plain(alerts), "pagination": pagination}
            if start_dt or end_dt:
                result["date_filter"] = {"from": start_dt, "to": end_dt, "scanned": scanned, "truncated": truncated}
            self.output_data(result)
            return

        if truncated:
            self.display_warning(
                f"Scanned the newest {scanned} alerts only; narrow the range or add --status/--check/--severity."
            )
        if not alerts:
            self.display_info("No alerts found.")
            return

        table = Table(title="Alerts", header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Status")
        table.add_column("Severity")
        table.add_column("Title", max_width=40)
        table.add_column("Check", max_width=28)
        table.add_column("Fired (UTC)")
        table.add_column("Duration", justify="right")
        for alert in alerts:
            table.add_row(
                text(alert.id),
                styled(alert.status, STATUS_STYLE),
                styled(alert.severity, SEVERITY_STYLE),
                text(alert.title),
                text(alert.check_name, text(alert.check_id)),
                format_dt(alert.fired_at),
                _duration(alert.duration),
            )
        self.console.print(table)
        if start_dt or end_dt:
            self.console.print(f"[dim]{len(alerts)} alert(s) fired in range (filtered client-side from {scanned})[/dim]")
        else:
            line = pagination_line(pagination, len(alerts))
            if line:
                self.console.print(line)

    def _scan(self, api, filters, start: Optional[datetime], end: Optional[datetime]) -> Tuple[List[Any], int, bool]:
        """The API has no date filter; alerts come newest-first, so page until we pass --from."""
        matched, scanned = [], 0
        for page in range(1, SCAN_MAX_PAGES + 1):
            data = api.v1_alerts_get(**filters, page=page, per_page=SCAN_PAGE_SIZE)
            alerts = data.alerts or []
            scanned += len(alerts)
            reached_older = False
            for alert in alerts:
                fired = parse_dt(alert.fired_at)
                if fired is None:
                    continue
                if start and fired < start:
                    reached_older = True
                    continue
                if end and fired > end:
                    continue
                matched.append(alert)
            if reached_older or not alerts or as_dict(data.pagination).get("has_next") is not True:
                return matched, scanned, False
        return matched, scanned, True

    def get_alert(self, alert_id: str):
        try:
            alert = self._api().v1_alerts_alert_id_get(alert_id=alert_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get alert", e)

        if self.machine_output:
            self.output_model(alert)
            return
        self._render_alert(alert)

    def _render_alert(self, alert):
        rule = text(alert.rule_name, "")
        check = text(alert.check_name, "")
        lines = [
            f"[bold cyan]Status:[/bold cyan] {styled(alert.status, STATUS_STYLE)}",
            f"[bold cyan]Severity:[/bold cyan] {styled(alert.severity, SEVERITY_STYLE)}",
            f"[bold cyan]Rule:[/bold cyan] {rule + ' ' if rule else ''}[dim]({text(alert.rule_id)})[/dim]",
            f"[bold cyan]Check:[/bold cyan] {check + ' ' if check else ''}[dim]({text(alert.check_id)})[/dim]",
            f"[bold cyan]Fired:[/bold cyan] {format_dt(alert.fired_at, '%Y-%m-%d %H:%M:%S')} UTC",
        ]
        if alert.acknowledged_at:
            by = f" by {alert.acknowledged_by_id}" if alert.acknowledged_by_id else ""
            lines.append(f"[bold cyan]Acknowledged:[/bold cyan] {format_dt(alert.acknowledged_at, '%Y-%m-%d %H:%M:%S')} UTC{by}")
        if alert.resolved_at:
            lines.append(f"[bold cyan]Resolved:[/bold cyan] {format_dt(alert.resolved_at, '%Y-%m-%d %H:%M:%S')} UTC")
        lines.append(f"[bold cyan]Duration:[/bold cyan] {_duration(alert.duration)}")
        lines.append(f"[bold cyan]Notifications sent:[/bold cyan] {text(alert.notification_count, '0')}")

        summary = as_dict(alert.regional_summary)
        if isinstance(summary.get("total_regions"), int):
            regions = ", ".join(text(r) for r in as_list(summary.get("regions")))
            lines.append(
                f"[bold cyan]Regions:[/bold cyan] {text(summary.get('failed_regions'))} of "
                f"{summary['total_regions']} failed{f' ({regions})' if regions else ''}"
            )
        metadata = {k: v for k, v in as_dict(alert.alert_metadata).items() if isinstance(v, (str, int, float, bool))}
        if metadata:
            lines.append("[bold cyan]Metadata:[/bold cyan] " + ", ".join(f"{k}={text(v)}" for k, v in metadata.items()))
        if alert.description:
            lines.append(f"\n{alert.description}")

        self.console.print(Panel("\n".join(lines), title=f"🔔 {text(alert.title, 'Alert')} [dim]{text(alert.id)}[/dim]",
                                 border_style="red" if alert.status == "firing" else "cyan", padding=(1, 2)))

        results = [r for r in as_list(alert.trigger_results) if isinstance(r, dict)]
        if results:
            table = Table(title="Triggering results", header_style="bold magenta")
            table.add_column("Result ID", style="cyan")
            table.add_column("Primary")
            table.add_column("Status")
            table.add_column("Region")
            table.add_column("Time (UTC)")
            table.add_column("Error", max_width=50)
            for r in results:
                table.add_row(
                    text(r.get("result_id")),
                    "★" if r.get("is_primary") is True else "",
                    styled(r.get("status"), STATUS_STYLE),
                    text(r.get("region")),
                    format_dt(r.get("created_at"), "%Y-%m-%d %H:%M:%S"),
                    text(r.get("error_message"), ""),
                )
            self.console.print(table)

    def change_state(self, alert_id: str, action: str):
        try:
            api = self._api()
            if action == "acknowledge":
                alert = api.v1_alerts_alert_id_acknowledge_post(alert_id=alert_id)
            else:
                alert = api.v1_alerts_alert_id_resolve_post(alert_id=alert_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail(f"{action} alert", e)

        if self.machine_output:
            self.output_model(alert)
            return
        verb = "acknowledged" if action == "acknowledge" else "resolved"
        self.display_success(
            f"[bold cyan]ID:[/bold cyan] {text(alert.id, alert_id)}\n"
            f"[bold cyan]Title:[/bold cyan] {text(alert.title)}\n"
            f"[bold cyan]Status:[/bold cyan] {styled(alert.status, STATUS_STYLE)}",
            f"✅ Alert {verb}",
        )

    def notifications(self, alert_id: str):
        try:
            notifications = self._api().v1_alerts_alert_id_notifications_get(alert_id=alert_id) or []
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get alert notifications", e)

        if self.machine_output:
            self.output_model(notifications)
            return
        items = to_plain(notifications)
        if not items:
            self.display_info(f"No notifications were sent for alert {alert_id}.")
            return

        def channel_label(n):
            return text(n.get("channel_name"), text(n.get("channel_id"), "?"))

        items.sort(key=lambda n: (channel_label(n), text(n.get("created_at"), "")))
        table = Table(title=f"Notifications for alert {alert_id}", header_style="bold magenta")
        table.add_column("Channel", style="cyan")
        table.add_column("Type")
        table.add_column("Event")
        table.add_column("Status")
        table.add_column("Created (UTC)")
        table.add_column("Sent (UTC)")
        table.add_column("Retries", justify="right")
        table.add_column("Error", max_width=40)
        for n in items:
            table.add_row(
                channel_label(n),
                text(n.get("channel_type")),
                text(n.get("notification_type")),
                styled(n.get("status"), STATUS_STYLE),
                format_dt(n.get("created_at"), "%Y-%m-%d %H:%M:%S"),
                format_dt(n.get("sent_at"), "%Y-%m-%d %H:%M:%S"),
                text(n.get("retry_count"), "0"),
                text(n.get("error_message"), ""),
            )
        self.console.print(table)
        failed = sum(1 for n in items if n.get("status") == "failed")
        self.console.print(f"[dim]{len(items)} notification(s), {failed} failed[/dim]")

    def stats(self):
        try:
            stats = self._api().v1_alerts_stats_get()
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get alert stats", e)

        if self.machine_output:
            self.output_model(stats)
            return

        active = stats.active_alerts or 0
        body = (
            f"[bold cyan]Active alerts (firing + acknowledged):[/bold cyan] "
            f"{'[bold red]' if active else '[green]'}{active}{'[/bold red]' if active else '[/green]'}\n"
            f"[bold cyan]Alerts fired in the last 30 days:[/bold cyan] {text(stats.recent_alerts, '0')}\n"
            f"[bold cyan]Enabled rules:[/bold cyan] {text(stats.total_rules, '0')}\n"
            f"[bold cyan]Enabled channels:[/bold cyan] {text(stats.total_channels, '0')}"
        )
        breakdown = {k: v for k, v in as_dict(stats.severity_breakdown).items() if isinstance(v, int)}
        if breakdown:
            ordered = [s for s in SEVERITIES if s in breakdown] + sorted(k for k in breakdown if k not in SEVERITIES)
            body += "\n[bold cyan]Last 30 days by severity:[/bold cyan] " + "  ".join(
                f"{styled(s, SEVERITY_STYLE)} {breakdown[s]}" for s in ordered
            )
        self.console.print(Panel(body, title="📊 Alert statistics", border_style="cyan", padding=(1, 2)))


app = typer.Typer(
    name="alerts",
    help="🔔 Alerts: fired alerts, alert rules and notification channels",
    no_args_is_help=True,
)
app.add_typer(rules_app, name="rules")
app.add_typer(channels_app, name="channels")


@app.command("list")
def list_alerts(
    status: Optional[str] = typer.Option(
        None, "--status", help="active (firing + acknowledged), firing, acknowledged, resolved or suppressed"),
    check_id: Optional[str] = typer.Option(None, "--check", "-c", help="Only alerts of this check ID"),
    severity: Optional[str] = typer.Option(None, "--severity", help="low, medium, high or critical"),
    start: Optional[str] = typer.Option(
        None, "--from", help="Fired at/after (ISO 8601 or relative like 24h, 7d). Filtered client-side"),
    end: Optional[str] = typer.Option(None, "--to", help="Fired at/before (ISO 8601 or relative). Filtered client-side"),
    page: int = typer.Option(1, "--page", "-p", min=1, help="Page number (not used with --from/--to)"),
    per_page: int = typer.Option(20, "--per-page", "-s", min=1, max=100, help="Alerts per page (max 100)"),
):
    """List fired alerts, newest first"""
    from ..utils.config import get_output_format

    check_choice(status, ALERT_STATUSES, "--status")
    check_choice(severity, SEVERITIES, "--severity")
    if (start or end) and page != 1:
        raise typer.BadParameter("--page can't be combined with --from/--to (all matches are returned)",
                                 param_hint="--page")
    AlertsCommand(get_output_format()).list_alerts(status, check_id, severity, start, end, page, per_page)


@app.command("get")
def get_alert(alert_id: str = typer.Argument(..., help="Alert ID")):
    """Show an alert with its rule, check, timeline and triggering results"""
    from ..utils.config import get_output_format
    AlertsCommand(get_output_format()).get_alert(alert_id)


@app.command("ack")
def ack_alert(alert_id: str = typer.Argument(..., help="Alert ID (must be firing)")):
    """Acknowledge a firing alert"""
    from ..utils.config import get_output_format
    AlertsCommand(get_output_format()).change_state(alert_id, "acknowledge")


@app.command("resolve")
def resolve_alert(alert_id: str = typer.Argument(..., help="Alert ID (must be firing or acknowledged)")):
    """Manually resolve an active alert"""
    from ..utils.config import get_output_format
    AlertsCommand(get_output_format()).change_state(alert_id, "resolve")


@app.command("notifications")
def alert_notifications(alert_id: str = typer.Argument(..., help="Alert ID")):
    """Show the notification delivery log of an alert, grouped by channel"""
    from ..utils.config import get_output_format
    AlertsCommand(get_output_format()).notifications(alert_id)


@app.command("stats")
def alert_stats():
    """Show active/recent alert counts, severity breakdown and enabled rules/channels"""
    from ..utils.config import get_output_format
    AlertsCommand(get_output_format()).stats()
