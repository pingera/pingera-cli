"""
Extra component commands: `pngr pages components statuses|uptime-report`
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import typer
from rich.table import Table

from .base import BaseCommand
from .status_page_common import DESCRIPTIONS, as_dict, as_list, raw_json, styled, text
from ..utils.time_utils import format_duration, parse_time_arg

MAX_UPTIME_RANGE_DAYS = 183


def _uptime_style(value: Optional[float]) -> str:
    if value is None:
        return "white"
    return "green" if value >= 99.9 else "yellow" if value >= 99.0 else "red"


def _float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _seconds(value: Any) -> str:
    seconds = _float(value)
    if seconds is None:
        return "-"
    return "[green]0s[/green]" if seconds == 0 else format_duration(seconds)


def uptime_query(start: Optional[str], end: Optional[str]) -> Dict[str, str]:
    """Build the backend's start/end query (dates as YYYY-MM-DD); validates before any API call."""
    start_dt = parse_time_arg(start, "--from")
    end_dt = parse_time_arg(end, "--to")
    if start_dt and end_dt and start_dt > end_dt:
        raise typer.BadParameter("--from must be before --to", param_hint="--from")
    query = {}
    if start_dt:
        query["start"] = start_dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    if end_dt:
        query["end"] = end_dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    return query


class ComponentExtrasCommand(BaseCommand):
    """Component status reference and bulk uptime"""

    def _api(self):
        from pingera.api import StatusPagesComponentsApi
        return self.api(StatusPagesComponentsApi)

    def statuses(self):
        try:
            values = self._api().v1_component_statuses_get() or []
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get component statuses", e)

        if self.machine_output:
            self.output_data(list(values))
            return
        table = Table(title="Component statuses", header_style="bold magenta")
        table.add_column("Status")
        table.add_column("Meaning")
        for value in values:
            table.add_row(styled(value), DESCRIPTIONS.get(str(value), ""))
        self.console.print(table)

    def uptime_report(self, page_id: str, component_ids: List[str], start: Optional[str], end: Optional[str],
                      include_groups: bool):
        query = uptime_query(start, end)
        start_dt = parse_time_arg(start, "--from")
        end_dt = parse_time_arg(end, "--to") or datetime.now(timezone.utc)
        if start_dt and end_dt - start_dt > timedelta(days=MAX_UPTIME_RANGE_DAYS):
            self.display_warning(f"The API limits uptime to ~6 months ({MAX_UPTIME_RANGE_DAYS} days); "
                                 "the start date will be moved forward.")
        try:
            api = self._api()
            ids = list(component_ids)
            if not ids:
                components = api.v1_pages_page_id_components_get(page_id=page_id) or []
                ids = [c.id for c in components if c.id and (include_groups or not c.group)]
                if not ids:
                    if self.machine_output:
                        self.output_data({"page_id": page_id, **query, "components": []})
                    else:
                        self.display_info(f"No components on page {page_id}.")
                    return
            data = raw_json(
                api, "v1_pages_page_id_components_uptime_post", query=query,
                page_id=page_id, component_uptime_bulk_request={"component_ids": ids},
            )
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get component uptime", e)

        rows = [as_dict(r) for r in as_list(data)]
        if self.machine_output:
            self.output_data({"page_id": page_id, **query, "components": rows})
            return
        if not rows:
            self.display_info("No uptime data returned.")
            return

        first = rows[0]
        period = f"{text(first.get('range_start'))} → {text(first.get('range_end'))}"
        table = Table(title=f"Component uptime: {page_id} ({period})", header_style="bold magenta")
        table.add_column("Component", style="green")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Uptime", justify="right")
        table.add_column("Major outage", justify="right")
        table.add_column("Partial outage", justify="right")
        table.add_column("Incidents", justify="right")
        warnings = set()
        for row in rows:
            pct = _float(row.get("uptime_percentage"))
            style = _uptime_style(pct)
            events = as_list(as_dict(row.get("related_events")).get("id"))
            warnings.update(str(w) for w in as_list(row.get("warnings")))
            table.add_row(
                text(row.get("name")),
                text(row.get("id")),
                f"[{style}]{pct:.2f}%[/{style}]" if pct is not None else "-",
                _seconds(row.get("major_outage")),
                _seconds(row.get("partial_outage")),
                str(len(events)),
            )
        self.console.print(table)
        for warning in sorted(warnings):
            self.console.print(f"[yellow]⚠ {warning}[/yellow]")
        self.console.print("[dim]Outage columns are total outage time from incidents (major/critical → major, "
                           "minor → partial). Default period: last 90 days.[/dim]")


def register(app: typer.Typer):
    """Attach `statuses` and `uptime-report` to the components Typer app."""

    from ..utils.config import get_output_format

    @app.command("statuses")
    def statuses():
        """List the valid component statuses"""
        ComponentExtrasCommand(get_output_format()).statuses()

    @app.command("uptime-report")
    def uptime_report(
        page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
        component_ids: Optional[List[str]] = typer.Option(None, "--component-id", "-c", help="Only this component or group (repeatable). Default: all components of the page"),
        start: Optional[str] = typer.Option(None, "--from", help="Start date (ISO 8601 or relative like 30d). Default: 90 days ago; max range ~6 months"),
        end: Optional[str] = typer.Option(None, "--to", help="End date (ISO 8601 or relative). Default: today"),
        include_groups: bool = typer.Option(False, "--include-groups", help="When listing all components, also include groups (group uptime = average of members)"),
    ):
        """Show uptime % and outage time for all (or selected) components of a page"""
        ComponentExtrasCommand(get_output_format()).uptime_report(page_id, component_ids or [], start, end, include_groups)
