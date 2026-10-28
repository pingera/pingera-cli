"""
Extra incident commands: `pngr pages incidents reference|log-past|schedule-maintenance`
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import typer
from rich.table import Table

from .base import BaseCommand
from .status_page_common import (
    COMPONENT_SPEC_HELP,
    DESCRIPTIONS,
    INCIDENT_IMPACTS,
    INCIDENT_STATUSES,
    iso,
    parse_component_statuses,
    parse_future_time,
    parse_past_time,
    styled,
    text,
)
from ..utils.time_utils import format_dt, format_duration

_REMINDER = re.compile(r"^\d+[mhd]$")


class IncidentExtrasCommand(BaseCommand):
    """Reference values, past incidents and scheduled maintenance"""

    def _api(self):
        from pingera.api import StatusPagesIncidentsApi
        return self.api(StatusPagesIncidentsApi)

    def reference(self):
        try:
            api = self._api()
            data = {
                "incident_statuses": list(api.v1_incident_statuses_get() or []),
                "maintenance_statuses": list(api.v1_maintenance_statuses_get() or []),
                "impacts": list(api.v1_incident_impacts_get() or []),
            }
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get incident reference values", e)

        if self.machine_output:
            self.output_data(data)
            return
        titles = {
            "incident_statuses": "Incident statuses (--status)",
            "maintenance_statuses": "Maintenance window statuses",
            "impacts": "Impacts (--impact)",
        }
        for key, values in data.items():
            table = Table(title=titles[key], header_style="bold magenta", title_justify="left")
            table.add_column("Value", min_width=14)
            table.add_column("Meaning", min_width=40)
            for value in values:
                table.add_row(styled(value), DESCRIPTIONS.get(str(value), ""))
            self.console.print(table)
        self.console.print("[dim]Component statuses: pngr pages components statuses[/dim]")

    def log_past(self, page_id: str, payload: Dict[str, Any]):
        try:
            incident = self._api().v1_pages_page_id_incidents_log_past_incident_post(page_id=page_id, log_past_incident=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("log past incident", e)

        if self.machine_output:
            self.output_model(incident)
            return
        updates = payload["incident_updates"]
        started, ended = updates[0]["created_at"], updates[-1]["created_at"]
        duration = (datetime.fromisoformat(ended.replace("Z", "+00:00")) -
                    datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds()
        self.display_success(
            f"ID: {text(incident.id)}\nName: {text(incident.name)}\nStatus: {text(incident.status)}\n"
            f"Impact: {text(incident.impact)}\nPeriod: {format_dt(started)} → {format_dt(ended)} UTC "
            f"({format_duration(duration)})\nUpdates: {len(updates)}",
            "✅ Past Incident Logged",
        )

    def schedule_maintenance(self, page_id: str, payload: Dict[str, Any]):
        try:
            incident = self._api().v1_pages_page_id_incidents_post(page_id=page_id, incident_create=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("schedule maintenance", e)

        if self.machine_output:
            self.output_model(incident)
            return
        lines = [
            f"ID: {text(incident.id)}",
            f"Name: {text(incident.name)}",
            f"Window: {format_dt(payload['scheduled_for'])} → {format_dt(payload['scheduled_until'])} UTC",
            f"Components: {len(payload.get('components') or {})}",
            "Starts automatically" if payload["scheduled_auto_in_progress"] else
            f"Start it manually: pngr pages incidents updates add {text(incident.id)} --page-id {page_id} --status in_progress",
        ]
        self.display_success("\n".join(lines), "✅ Maintenance Scheduled")


def _load_updates_file(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as e:
        raise typer.BadParameter(f"cannot read {path}: {e.strerror}", param_hint="--updates-file")
    except ValueError as e:
        raise typer.BadParameter(f"invalid JSON: {e}", param_hint="--updates-file")
    if isinstance(data, dict):
        data = data.get("incident_updates")
    if not isinstance(data, list) or not data:
        raise typer.BadParameter("must contain a non-empty JSON list of updates", param_hint="--updates-file")
    updates = []
    for i, item in enumerate(data, 1):
        if not isinstance(item, dict):
            raise typer.BadParameter(f"update #{i} is not an object", param_hint="--updates-file")
        missing = [k for k in ("status", "body", "created_at") if not item.get(k)]
        if missing:
            raise typer.BadParameter(f"update #{i} is missing {', '.join(missing)}", param_hint="--updates-file")
        if item["status"] not in INCIDENT_STATUSES:
            raise typer.BadParameter(f"update #{i}: status must be one of {', '.join(INCIDENT_STATUSES)}", param_hint="--updates-file")
        created = parse_past_time(str(item["created_at"]), f"--updates-file (update #{i} created_at)")
        components = item.get("components") or {}
        if not isinstance(components, dict):
            raise typer.BadParameter(f"update #{i}: components must be an object of ID: STATUS", param_hint="--updates-file")
        parse_component_statuses([f"{k}={v}" for k, v in components.items()], "--updates-file")
        updates.append({"status": item["status"], "body": str(item["body"]), "created_at": iso(created), "components": components})
    return sorted(updates, key=lambda u: u["created_at"])


def register(app: typer.Typer):
    """Attach `reference`, `log-past` and `schedule-maintenance` to the incidents Typer app."""

    from ..utils.config import get_output_format

    @app.command("reference")
    def reference():
        """Show valid incident statuses, maintenance statuses and impacts"""
        IncidentExtrasCommand(get_output_format()).reference()

    @app.command("log-past")
    def log_past(
        page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
        name: str = typer.Option(..., "--name", "-n", help="Incident title"),
        impact: str = typer.Option(..., "--impact", "-i", help=f"Impact: {', '.join(INCIDENT_IMPACTS)} (minor = partial outage, major/critical = major outage in uptime)"),
        started: Optional[str] = typer.Option(None, "--started", help="When it started (ISO 8601 or relative like 3d = 3 days ago)"),
        resolved: Optional[str] = typer.Option(None, "--resolved", help="When it was resolved (ISO 8601 or relative)"),
        body: Optional[str] = typer.Option(None, "--body", "-b", help="Description posted as the first update"),
        resolution: str = typer.Option("This incident has been resolved.", "--resolution", help="Message of the final 'resolved' update"),
        component: Optional[List[str]] = typer.Option(None, "--component", "-c", help=COMPONENT_SPEC_HELP + " during the incident (back to operational when resolved)"),
        updates_file: Optional[str] = typer.Option(None, "--updates-file", help='JSON file with the full timeline instead of --started/--resolved/--body: [{"status", "body", "created_at", "components": {ID: STATUS}}]'),
        notify: bool = typer.Option(False, "--notify/--no-notify", help="Notify subscribers (off by default for past incidents)"),
    ):
        """Record an incident that already happened (with its timeline) so it shows in history and uptime"""
        if impact not in INCIDENT_IMPACTS:
            raise typer.BadParameter(f"must be one of {', '.join(INCIDENT_IMPACTS)}", param_hint="--impact")
        if updates_file:
            if started or resolved or body or component:
                raise typer.BadParameter("--updates-file can't be combined with --started/--resolved/--body/--component",
                                         param_hint="--updates-file")
            updates = _load_updates_file(updates_file)
        else:
            if not started or not resolved or not body:
                raise typer.BadParameter("--started, --resolved and --body are required (or use --updates-file)",
                                         param_hint="--started")
            start_dt = parse_past_time(started, "--started")
            end_dt = parse_past_time(resolved, "--resolved")
            if end_dt <= start_dt:
                raise typer.BadParameter("must be after --started", param_hint="--resolved")
            components = parse_component_statuses(component) or {}
            updates = [
                {"status": "investigating", "body": body, "created_at": iso(start_dt), "components": components},
                {"status": "resolved", "body": resolution, "created_at": iso(end_dt),
                 "components": {cid: "operational" for cid in components}},
            ]
        payload = {"name": name, "impact": impact, "deliver_notifications": notify, "incident_updates": updates}
        IncidentExtrasCommand(get_output_format()).log_past(page_id, payload)

    @app.command("schedule-maintenance")
    def schedule_maintenance(
        page_id: str = typer.Option(..., "--page-id", "-p", help="Status page ID"),
        name: str = typer.Option(..., "--name", "-n", help="Maintenance title"),
        start: str = typer.Option(..., "--start", help="Window start, in the future (ISO 8601 or +2h / +1d from now)"),
        end: str = typer.Option(..., "--end", help="Window end (ISO 8601 or +3h / +1d from now)"),
        body: Optional[str] = typer.Option(None, "--body", "-b", help="Description shown on the status page"),
        component_ids: Optional[List[str]] = typer.Option(None, "--component-id", "-c", help="Affected component (repeatable)"),
        notify: bool = typer.Option(False, "--notify/--no-notify", help="Notify subscribers now that maintenance is scheduled"),
        auto_start: bool = typer.Option(True, "--auto-start/--no-auto-start", help="Switch to in_progress automatically at --start"),
        auto_complete: bool = typer.Option(True, "--auto-complete/--no-auto-complete", help="Switch to completed automatically at --end"),
        auto_components: bool = typer.Option(True, "--auto-component-status/--no-auto-component-status", help="Set components to under_maintenance at start and back to operational at the end"),
        transition_notify: bool = typer.Option(True, "--notify-transitions/--no-notify-transitions", help="Notify subscribers when the window starts and ends"),
        remind: bool = typer.Option(True, "--remind/--no-remind", help="Send reminders before the window starts"),
        reminders: str = typer.Option("24h,1h", "--reminders", help="When to remind, before start: comma-separated <n>m|h|d"),
    ):
        """Schedule a maintenance window (status 'scheduled', impact 'maintenance')"""
        start_dt = parse_future_time(start, "--start")
        end_dt = parse_future_time(end, "--end")
        if start_dt <= datetime.now(timezone.utc):
            raise typer.BadParameter("must be in the future", param_hint="--start")
        if end_dt <= start_dt:
            raise typer.BadParameter("must be after --start", param_hint="--end")
        intervals = [i.strip() for i in reminders.split(",") if i.strip()]
        if remind and (not intervals or not all(_REMINDER.match(i) for i in intervals)):
            raise typer.BadParameter("use a list like 24h,1h or 2d,30m", param_hint="--reminders")
        payload: Dict[str, Any] = {
            "name": name,
            "status": "scheduled",
            "impact": "maintenance",
            "scheduled_for": iso(start_dt),
            "scheduled_until": iso(end_dt),
            "deliver_notifications": notify,
            "scheduled_auto_in_progress": auto_start,
            "scheduled_auto_completed": auto_complete,
            "auto_transition_to_maintenance_state": auto_components,
            "auto_transition_to_operational_state": auto_components,
            "auto_transition_deliver_notifications_at_start": transition_notify,
            "auto_transition_deliver_notifications_at_end": transition_notify,
            "scheduled_remind_prior": remind,
        }
        if remind:
            payload["reminder_intervals"] = ",".join(intervals)
        if body is not None:
            payload["body"] = body
        if component_ids:
            # Same as the web UI: components stay operational until the window starts.
            payload["components"] = {cid: "operational" for cid in component_ids}
        IncidentExtrasCommand(get_output_format()).schedule_maintenance(page_id, payload)
