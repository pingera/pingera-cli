"""
Incident updates and postmortems: `pngr pages incidents updates|postmortem ...`
"""

import sys
from typing import Any, Dict, List, Optional

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from .base import BaseCommand
from .status_page_common import (
    COMPONENT_SPEC_HELP,
    INCIDENT_STATUSES,
    MAINTENANCE_STATUSES,
    as_dict,
    as_list,
    component_status_map,
    iso,
    parse_component_statuses,
    parse_past_time,
    styled,
    text,
    truncate,
)
from ..utils.time_utils import format_dt

UPDATE_STATUSES = INCIDENT_STATUSES + MAINTENANCE_STATUSES


class IncidentUpdatesCommand(BaseCommand):
    """Timeline updates of an incident"""

    def _api(self):
        from pingera.api import StatusPagesIncidentsApi
        return self.api(StatusPagesIncidentsApi)

    def list_updates(self, page_id: str, incident_id: str):
        try:
            updates = self._api().v1_pages_page_id_incidents_incident_id_incident_updates_get(
                page_id=page_id, incident_id=incident_id
            ) or []
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("list incident updates", e)

        if self.machine_output:
            self.output_model(updates)
            return
        if not updates:
            self.display_info(f"Incident {incident_id} has no updates.")
            return

        table = Table(title=f"Updates of incident {incident_id}", header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Posted (UTC)", no_wrap=True)
        table.add_column("Status")
        table.add_column("Notified", justify="center")
        table.add_column("Components")
        table.add_column("Message")
        for update in updates:
            components = component_status_map(update.components)
            notified = update.deliver_notifications
            table.add_row(
                text(update.id),
                format_dt(update.created_at),
                styled(update.status),
                "✓" if notified is True else "✗" if notified is False else "-",
                "\n".join(f"{cid}: {styled(st)}" for cid, st in components.items()) or "[dim]-[/dim]",
                truncate(update.body, 70),
            )
        self.console.print(table)
        self.console.print(f"[dim]{len(updates)} update(s)[/dim]")

    def add_update(self, page_id: str, incident_id: str, status: Optional[str], body: Optional[str],
                   components: Optional[Dict[str, str]], notify: bool):
        payload: Dict[str, Any] = {"deliver_notifications": notify}
        if status is not None:
            payload["status"] = status
        if body is not None:
            payload["body"] = body
        if components is not None:
            payload["components"] = components
        try:
            incident = self._api().v1_pages_page_id_incidents_incident_id_patch(
                page_id=page_id, incident_id=incident_id, incident_update_schema_edit=payload
            )
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("add incident update", e)

        if self.machine_output:
            self.output_model(incident)
            return
        updates = [as_dict(u) for u in as_list(incident.incident_updates)]
        newest = max(updates, key=lambda u: str(u.get("created_at") or ""), default={})
        lines = [
            f"Incident: {text(incident.name)} ({text(incident.id or incident_id)})",
            f"Status: {text(incident.status)}",
        ]
        if newest.get("id"):
            lines.append(f"Update ID: {newest['id']}")
        if components:
            lines.append("Components: " + ", ".join(f"{cid}={st}" for cid, st in components.items()))
        lines.append("Subscribers notified" if notify else "No notifications sent")
        self.display_success("\n".join(lines), "✅ Update Posted")

    def edit_update(self, page_id: str, incident_id: str, update_id: str, body: Optional[str],
                    created_at: Optional[str], components: Optional[Dict[str, str]]):
        payload: Dict[str, Any] = {}
        if body is not None:
            payload["body"] = body
        if created_at is not None:
            payload["created_at"] = created_at
        if components is not None:
            payload["components"] = components
        try:
            update = self._api().v1_pages_page_id_incidents_incident_id_incident_updates_incident_update_id_patch(
                page_id=page_id, incident_id=incident_id, incident_update_id=update_id, incident_update_edit=payload,
            )
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("edit incident update", e)

        if self.machine_output:
            self.output_model(update)
            return
        lines = [f"Update ID: {text(update.id, update_id)}", "Changed: " + ", ".join(payload)]
        if update.created_at:
            lines.append(f"Posted at: {format_dt(update.created_at, '%Y-%m-%d %H:%M:%S')} UTC")
        self.display_success("\n".join(lines), "✅ Update Edited")

    def delete_update(self, page_id: str, incident_id: str, update_id: str, confirm: bool):
        if not confirm and not Confirm.ask(f"Delete update {update_id} of incident {incident_id}?", console=self.error_console):
            self.error_console.print("[yellow]Operation cancelled.[/yellow]")
            return
        try:
            self._api().v1_pages_page_id_incidents_incident_id_incident_updates_incident_update_id_delete(
                page_id=page_id, incident_id=incident_id, incident_update_id=update_id
            )
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("delete incident update", e)

        if self.machine_output:
            self.output_data({"deleted": True, "id": update_id})
        else:
            self.display_success(f"Update {update_id} deleted. The incident's status and timestamps were "
                                 "recalculated from the remaining updates.", "✅ Update Deleted")


class PostmortemCommand(BaseCommand):
    """Incident postmortems (draft → publish)"""

    def _api(self):
        from pingera.api import StatusPagesIncidentsApi
        return self.api(StatusPagesIncidentsApi)

    def get(self, page_id: str, incident_id: str):
        try:
            pm = self._api().v1_pages_page_id_incidents_incident_id_postmortem_get(page_id=page_id, incident_id=incident_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get postmortem", e)

        if self.machine_output:
            self.output_model(pm)
            return
        published = bool(pm.published_at)
        has_unpublished_draft = bool(pm.body_draft) and pm.body_draft != pm.body
        state = (f"[green]Published[/green] {format_dt(pm.published_at)} UTC" if published
                 else "[yellow]Draft (not published)[/yellow]")
        info = (
            f"[bold cyan]Status:[/bold cyan] {state}\n"
            f"[bold cyan]Draft updated:[/bold cyan] {format_dt(pm.body_draft_updated_at)}\n"
            f"[bold cyan]Notify subscribers:[/bold cyan] {text(pm.notify_subscribers)}\n"
            f"[bold cyan]Preview key:[/bold cyan] {text(pm.preview_key)}"
        )
        self.console.print(Panel(info, title=f"📝 Postmortem: incident {incident_id}", border_style="blue", padding=(1, 2)))
        if published and pm.body:
            self.console.print(Panel(Markdown(pm.body), title="Published", border_style="green"))
        if has_unpublished_draft or (not published and pm.body_draft):
            title = "Draft (unpublished changes)" if published else "Draft"
            self.console.print(Panel(Markdown(pm.body_draft), title=title, border_style="yellow"))
            self.console.print(f"[dim]💡 Publish: pngr pages incidents postmortem publish {incident_id} --page-id {page_id}[/dim]")

    def set(self, page_id: str, incident_id: str, body: str, notify: Optional[bool]):
        payload: Dict[str, Any] = {"body_draft": body}
        if notify is not None:
            payload["notify_subscribers"] = notify
        try:
            pm = self._api().v1_pages_page_id_incidents_incident_id_postmortem_put(
                page_id=page_id, incident_id=incident_id, incident_postmortem=payload
            )
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("save postmortem", e)

        if self.machine_output:
            self.output_model(pm)
            return
        self.display_success(
            f"Draft saved for incident {incident_id} ({len(body)} characters).\n"
            f"Publish it with: pngr pages incidents postmortem publish {incident_id} --page-id {page_id}",
            "✅ Postmortem Draft Saved",
        )

    def publish(self, page_id: str, incident_id: str, notify: Optional[bool]):
        try:
            api = self._api()
            if notify is not None:
                api.v1_pages_page_id_incidents_incident_id_postmortem_put(
                    page_id=page_id, incident_id=incident_id, incident_postmortem={"notify_subscribers": notify}
                )
            pm = api.v1_pages_page_id_incidents_incident_id_postmortem_publish_put(page_id=page_id, incident_id=incident_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("publish postmortem", e)

        if self.machine_output:
            self.output_model(pm)
            return
        self.display_success(
            f"Postmortem of incident {incident_id} is now public.\nPublished at: {format_dt(pm.published_at)} UTC",
            "✅ Postmortem Published",
        )


updates_app = typer.Typer(name="updates", help="🧾 Manage the update timeline of an incident", no_args_is_help=True)
postmortem_app = typer.Typer(name="postmortem", help="📝 Write and publish incident postmortems", no_args_is_help=True)

PAGE_ID = typer.Option(..., "--page-id", "-p", help="Status page ID")
INCIDENT_ID = typer.Argument(..., help="Incident ID")


def _output_format():
    from ..utils.config import get_output_format
    return get_output_format()


@updates_app.command("list")
def list_updates(incident_id: str = INCIDENT_ID, page_id: str = PAGE_ID):
    """List all updates of an incident (newest first)"""
    IncidentUpdatesCommand(_output_format()).list_updates(page_id, incident_id)


@updates_app.command("add")
def add_update(
    incident_id: str = INCIDENT_ID,
    page_id: str = PAGE_ID,
    status: Optional[str] = typer.Option(None, "--status", "-s", help=f"New status: {', '.join(INCIDENT_STATUSES)} (incidents) or {', '.join(MAINTENANCE_STATUSES)} (maintenance). Default: unchanged"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Update message shown on the status page"),
    component: Optional[List[str]] = typer.Option(None, "--component", "-c", help=COMPONENT_SPEC_HELP + ". Default: keep the previous update's component statuses"),
    notify: bool = typer.Option(True, "--notify/--no-notify", help="Notify page subscribers about this update"),
):
    """Post a new update to an incident (changes its status, component statuses and notifies subscribers)"""
    if status is not None and status not in UPDATE_STATUSES:
        raise typer.BadParameter(f"must be one of {', '.join(UPDATE_STATUSES)}", param_hint="--status")
    if status is None and body is None:
        raise typer.BadParameter("pass --status and/or --body", param_hint="--status")
    components = parse_component_statuses(component)
    IncidentUpdatesCommand(_output_format()).add_update(page_id, incident_id, status, body, components, notify)


@updates_app.command("edit")
def edit_update(
    incident_id: str = INCIDENT_ID,
    update_id: str = typer.Argument(..., help="Incident update ID"),
    page_id: str = PAGE_ID,
    body: Optional[str] = typer.Option(None, "--body", "-b", help="New message text"),
    posted_at: Optional[str] = typer.Option(None, "--posted-at", help="Backdate the update (ISO 8601 or relative like 2h = 2 hours ago); not in the future"),
    component: Optional[List[str]] = typer.Option(None, "--component", "-c", help=COMPONENT_SPEC_HELP + ". Replaces the update's whole component list"),
    clear_components: bool = typer.Option(False, "--clear-components", help="Remove all components from this update"),
):
    """Edit an existing update: fix its text, time or affected components (no notifications are sent)"""
    if component and clear_components:
        raise typer.BadParameter("use either --component or --clear-components", param_hint="--clear-components")
    components = {} if clear_components else parse_component_statuses(component)
    created_at = iso(parse_past_time(posted_at, "--posted-at"))
    if body is None and created_at is None and components is None:
        raise typer.BadParameter("pass --body, --posted-at, --component or --clear-components", param_hint="--body")
    IncidentUpdatesCommand(_output_format()).edit_update(page_id, incident_id, update_id, body, created_at, components)


@updates_app.command("delete")
def delete_update(
    incident_id: str = INCIDENT_ID,
    update_id: str = typer.Argument(..., help="Incident update ID"),
    page_id: str = PAGE_ID,
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """Delete an update (an incident must keep at least one update)"""
    IncidentUpdatesCommand(_output_format()).delete_update(page_id, incident_id, update_id, confirm)


@postmortem_app.command("get")
def get_postmortem(incident_id: str = INCIDENT_ID, page_id: str = PAGE_ID):
    """Show the postmortem of an incident (published text and pending draft)"""
    PostmortemCommand(_output_format()).get(page_id, incident_id)


@postmortem_app.command("set")
def set_postmortem(
    incident_id: str = INCIDENT_ID,
    page_id: str = PAGE_ID,
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Postmortem text (Markdown)"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Read the postmortem from a Markdown file ('-' for stdin)"),
    notify: Optional[bool] = typer.Option(None, "--notify-subscribers/--no-notify-subscribers", help="Store whether subscribers should be notified on publish"),
):
    """Create or replace the postmortem draft (publish separately)"""
    if (body is None) == (file is None):
        raise typer.BadParameter("pass exactly one of --body or --file", param_hint="--body/--file")
    if file is not None:
        try:
            body = sys.stdin.read() if file == "-" else open(file, encoding="utf-8").read()
        except OSError as e:
            raise typer.BadParameter(f"cannot read {file}: {e.strerror}", param_hint="--file")
    if not body.strip():
        raise typer.BadParameter("postmortem text is empty", param_hint="--body/--file")
    PostmortemCommand(_output_format()).set(page_id, incident_id, body, notify)


@postmortem_app.command("publish")
def publish_postmortem(
    incident_id: str = INCIDENT_ID,
    page_id: str = PAGE_ID,
    notify: Optional[bool] = typer.Option(None, "--notify-subscribers/--no-notify-subscribers", help="Set the postmortem's notify-subscribers flag before publishing"),
):
    """Publish the current draft on the status page"""
    PostmortemCommand(_output_format()).publish(page_id, incident_id, notify)
