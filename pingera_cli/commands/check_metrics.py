"""
Check analytics commands: uptime, status history, response times and result stats
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .base import BaseCommand, to_plain
from ..utils.time_utils import format_dt, format_duration, parse_time_arg

_STATUS_STYLE = {
    "ok": "green",
    "degraded": "yellow",
    "failed": "red",
    "timeout": "red",
    "no_data": "dim",
    "paused": "dim",
    "pending": "dim",
}


def _status_text(status: Optional[str]) -> str:
    if not status:
        return "-"
    style = _STATUS_STYLE.get(str(status).lower(), "white")
    return f"[{style}]{status}[/{style}]"


def _uptime_style(value: Optional[float]) -> str:
    if value is None:
        return "white"
    return "green" if value >= 99.9 else "yellow" if value >= 99.0 else "red"


def _ms(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.0f}ms"
    except (TypeError, ValueError):
        return str(value)


def _region_rows(data: Any) -> Dict[str, List[Dict[str, Any]]]:
    """Normalize {region: [bucket, ...]} responses, dropping anything malformed (the schema is untyped)."""
    if not isinstance(data, dict):
        return {}
    return {
        str(region): [row for row in rows if isinstance(row, dict)]
        for region, rows in data.items()
        if isinstance(rows, list)
    }


class CheckMetricsCommand(BaseCommand):
    """Read-only analytics for monitoring checks"""

    def __init__(self, output_format: Optional[str] = None):
        super().__init__(output_format)

    def _checks_api(self):
        from pingera.api import ChecksApi
        return self.api(ChecksApi)

    def _unified_api(self):
        from pingera.api import ChecksUnifiedResultsApi
        return self.api(ChecksUnifiedResultsApi)

    def uptime(self, check_id: str, start: Optional[str], end: Optional[str], hourly: bool):
        start_time = parse_time_arg(start, "--from")
        end_time = parse_time_arg(end, "--to")
        try:
            data = self._checks_api().v1_checks_check_id_uptime_get(
                check_id=check_id, start_time=start_time, end_time=end_time
            )
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get check uptime", e)

        if self.machine_output:
            self.output_data({"check_id": check_id, **to_plain(data)})
            return

        hours = data.uptime_data or []
        summary = data.summary
        uptime_pct = float(summary.uptime) if summary and summary.uptime is not None else None
        style = _uptime_style(uptime_pct)

        period = "last 24 hours"
        if hours:
            period = f"{format_dt(hours[0].hour)} → {format_dt(hours[-1].hour)} UTC"

        strip = Text()
        for hour in hours:
            strip.append("▇", style=_STATUS_STYLE.get(hour.status or "no_data", "white"))

        uptime_display = f"[{style}]{uptime_pct:.2f}%[/{style}]" if uptime_pct is not None else "-"
        checks_run = summary.checks if summary and summary.checks is not None else "-"
        body = (
            f"[bold cyan]Period:[/bold cyan] {period}\n"
            f"[bold cyan]Uptime:[/bold cyan] {uptime_display}\n"
            f"[bold cyan]Avg response time:[/bold cyan] {_ms(summary.avg_response_time if summary else None)}\n"
            f"[bold cyan]Checks executed:[/bold cyan] {checks_run}"
        )
        self.console.print(Panel(body, title=f"📈 Uptime: {check_id}", border_style="cyan", padding=(1, 2)))
        if hours:
            self.console.print(strip)
            self.console.print(
                "[dim]One bar per hour: [green]ok[/green] [yellow]degraded[/yellow] [red]failed[/red] no data[/dim]"
            )

        if hourly and hours:
            table = Table(title="Hourly uptime (UTC)", header_style="bold magenta")
            table.add_column("Hour")
            table.add_column("Status")
            table.add_column("Uptime", justify="right")
            for hour in hours:
                table.add_row(
                    format_dt(hour.hour),
                    _status_text(hour.status),
                    "-" if hour.status == "no_data" else f"{float(hour.uptime or 0):.1f}%",
                )
            self.console.print(table)

    def status_history(self, check_id: str, page: int, page_size: int):
        try:
            data = self._checks_api().v1_checks_check_id_status_history_get(
                check_id=check_id, page=page, page_size=page_size
            )
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get status history", e)

        periods = data.status_history or []
        if self.machine_output:
            self.output_data({"check_id": check_id, **to_plain(data)})
            return

        if not periods:
            self.display_info(f"No status changes recorded for check {check_id}.")
            return

        table = Table(title=f"Status history: {check_id}", header_style="bold magenta")
        table.add_column("Status")
        table.add_column("Started (UTC)")
        table.add_column("Ended (UTC)")
        table.add_column("Duration", justify="right")
        for period in periods:
            duration = None
            if period.started_at and period.ended_at:
                duration = (period.ended_at - period.started_at).total_seconds()
            table.add_row(
                _status_text(period.status),
                format_dt(period.started_at, "%Y-%m-%d %H:%M:%S"),
                format_dt(period.ended_at, "%Y-%m-%d %H:%M:%S") if period.ended_at else "[bold]ongoing[/bold]",
                format_duration(duration) if duration is not None else "-",
            )
        self.console.print(table)
        self._print_pagination(data.pagination, len(periods))

    def response_times(self, check_id: str, start: Optional[str], end: Optional[str],
                       region: Optional[str], status: Optional[str], buckets: bool):
        params = {
            "check_id": check_id,
            "start_date": parse_time_arg(start, "--from"),
            "end_date": parse_time_arg(end, "--to"),
            "region": region,
            "status": status.lower() if status else None,
        }
        try:
            data = self._unified_api().v1_checks_check_id_response_times_get(**params)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get response times", e)

        data = _region_rows(data)
        if self.machine_output:
            self.output_data({"check_id": check_id, "regions": data})
            return

        if not data:
            self.display_info("No results in this period.")
            return

        summary = Table(title=f"Response times: {check_id}", header_style="bold magenta")
        summary.add_column("Region")
        summary.add_column("Samples", justify="right")
        summary.add_column("Avg", justify="right")
        summary.add_column("Worst p95", justify="right")
        summary.add_column("Worst p99", justify="right")
        for region_name, rows in sorted(data.items()):
            rows = rows or []
            samples = sum(int(r.get("sample_count") or 0) for r in rows)
            weighted = sum(float(r.get("avg_response_time") or 0) * int(r.get("sample_count") or 0) for r in rows)
            p95 = max((float(r["p95_response_time"]) for r in rows if r.get("p95_response_time") is not None), default=None)
            p99 = max((float(r["p99_response_time"]) for r in rows if r.get("p99_response_time") is not None), default=None)
            summary.add_row(region_name, str(samples), _ms(weighted / samples if samples else None), _ms(p95), _ms(p99))
        self.console.print(summary)

        if buckets:
            for region_name, rows in sorted(data.items()):
                table = Table(title=f"{region_name}", header_style="bold magenta")
                for col in ("Time (UTC)", "Samples", "Avg", "p95", "p99"):
                    table.add_column(col, justify="left" if col.startswith("Time") else "right")
                for r in rows or []:
                    table.add_row(
                        format_dt(r.get("time_bucket")),
                        str(r.get("sample_count", "-")),
                        _ms(r.get("avg_response_time")),
                        _ms(r.get("p95_response_time")),
                        _ms(r.get("p99_response_time")),
                    )
                self.console.print(table)
        else:
            self.console.print("[dim]💡 Add --buckets to see the per-interval breakdown[/dim]")

    def stats(self, check_id: Optional[str], start: Optional[str], end: Optional[str], region: Optional[str],
              check_type: Optional[str], result_type: Optional[str], has_alerts: Optional[bool], buckets: bool):
        params = {
            "check_id": check_id,
            "start_date": parse_time_arg(start, "--from"),
            "end_date": parse_time_arg(end, "--to"),
            "region": region,
            "check_type": check_type,
            "result_type": result_type,
            "has_alerts": has_alerts,
        }
        try:
            data = self._unified_api().v1_checks_status_history_get(**params)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get result stats", e)

        data = _region_rows(data)
        if self.machine_output:
            self.output_data({"check_id": check_id, "regions": data})
            return

        if not data:
            self.display_info("No results in this period.")
            return

        statuses = ("ok", "failed", "degraded", "timeout")
        totals: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for region_name, rows in data.items():
            for r in rows or []:
                totals[region_name]["total"] += int(r.get("total_count") or 0)
                for s in statuses:
                    totals[region_name][s] += int(r.get(f"{s}_count") or 0)

        title = f"Result stats: {check_id}" if check_id else "Result stats: all checks"
        table = Table(title=title, header_style="bold magenta")
        table.add_column("Region")
        table.add_column("Total", justify="right")
        for s in statuses:
            table.add_column(s.capitalize(), justify="right", style=_STATUS_STYLE[s])
        table.add_column("Success rate", justify="right")
        grand: Dict[str, int] = defaultdict(int)
        for region_name in sorted(totals):
            t = totals[region_name]
            for k, v in t.items():
                grand[k] += v
            table.add_row(region_name, str(t["total"]), *[str(t[s]) for s in statuses], self._rate(t))
        if len(totals) > 1:
            table.add_row("[bold]All regions[/bold]", str(grand["total"]), *[str(grand[s]) for s in statuses], self._rate(grand))
        self.console.print(table)

        if buckets:
            for region_name, rows in sorted(data.items()):
                bt = Table(title=region_name, header_style="bold magenta")
                bt.add_column("Time (UTC)")
                bt.add_column("Total", justify="right")
                for s in statuses:
                    bt.add_column(s.capitalize(), justify="right", style=_STATUS_STYLE[s])
                for r in rows or []:
                    bt.add_row(format_dt(r.get("time_bucket")), str(r.get("total_count", 0)),
                               *[str(r.get(f"{s}_count", 0)) for s in statuses])
                self.console.print(bt)
        else:
            self.console.print("[dim]💡 Add --buckets to see the per-interval breakdown[/dim]")

    @staticmethod
    def _rate(t: Dict[str, int]) -> str:
        if not t.get("total"):
            return "-"
        rate = t["ok"] / t["total"] * 100
        style = _uptime_style(rate)
        return f"[{style}]{rate:.2f}%[/{style}]"

    def _print_pagination(self, pagination: Optional[Dict[str, Any]], shown: int):
        if not pagination:
            return
        page = pagination.get("page")
        total_pages = pagination.get("total_pages")
        total_items = pagination.get("total_items")
        self.console.print(f"[dim]Showing {shown} of {total_items} • page {page} of {total_pages}[/dim]")


def register(app: typer.Typer):
    """Attach analytics commands to the `checks` Typer app."""

    from ..utils.config import get_output_format

    @app.command("uptime")
    def uptime(
        check_id: str = typer.Argument(..., help="Check ID"),
        start: Optional[str] = typer.Option(None, "--from", help="Start (ISO 8601 or relative like 7d, 24h). Default: 24h ago"),
        end: Optional[str] = typer.Option(None, "--to", help="End (ISO 8601 or relative). Default: now"),
        hourly: bool = typer.Option(False, "--hourly", help="Show the hour-by-hour table"),
    ):
        """Show uptime percentage, average response time and an hourly status strip for a check"""
        CheckMetricsCommand(get_output_format()).uptime(check_id, start, end, hourly)

    @app.command("status-history")
    def status_history(
        check_id: str = typer.Argument(..., help="Check ID"),
        page: int = typer.Option(1, "--page", "-p", help="Page number"),
        page_size: int = typer.Option(20, "--page-size", "-s", help="Items per page (max 100)"),
    ):
        """List status periods of a check (when it went ok/failed/degraded and for how long)"""
        CheckMetricsCommand(get_output_format()).status_history(check_id, page, page_size)

    @app.command("response-times")
    def response_times(
        check_id: str = typer.Argument(..., help="Check ID"),
        start: Optional[str] = typer.Option(None, "--from", help="Start (ISO 8601 or relative like 7d). Default: 24h ago; max 6 months"),
        end: Optional[str] = typer.Option(None, "--to", help="End (ISO 8601 or relative). Default: now"),
        region: Optional[str] = typer.Option(None, "--region", "-r", help="Only this region"),
        status: Optional[str] = typer.Option(None, "--status", help="Only results with this status (ok, failed, degraded, timeout)"),
        buckets: bool = typer.Option(False, "--buckets", help="Show per-interval avg/p95/p99 for each region"),
    ):
        """Show average, p95 and p99 response times per region"""
        CheckMetricsCommand(get_output_format()).response_times(check_id, start, end, region, status, buckets)

    @app.command("stats")
    def stats(
        check_id: Optional[str] = typer.Argument(None, help="Check ID (omit for all checks in the organization)"),
        start: Optional[str] = typer.Option(None, "--from", help="Start (ISO 8601 or relative like 7d). Default: 24h ago; max 6 months"),
        end: Optional[str] = typer.Option(None, "--to", help="End (ISO 8601 or relative). Default: now"),
        region: Optional[str] = typer.Option(None, "--region", "-r", help="Only this region"),
        check_type: Optional[str] = typer.Option(None, "--type", "-t", help="Only checks of this type"),
        result_type: Optional[str] = typer.Option(None, "--result-type", help="regular or on_demand"),
        has_alerts: Optional[bool] = typer.Option(None, "--with-alerts/--without-alerts", help="Only results that did / did not trigger alerts"),
        buckets: bool = typer.Option(False, "--buckets", help="Show per-interval counts for each region"),
    ):
        """Count results by status (ok/failed/degraded/timeout) per region, for one check or all checks"""
        if result_type and result_type not in ("regular", "on_demand"):
            raise typer.BadParameter("must be 'regular' or 'on_demand'", param_hint="--result-type")
        CheckMetricsCommand(get_output_format()).stats(
            check_id, start, end, region, check_type, result_type, has_alerts, buckets
        )
