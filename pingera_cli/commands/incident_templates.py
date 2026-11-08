"""
Incident and maintenance templates: `pngr pages incidents templates ...`

Templates are page-scoped presets (title, message, incident status, components, maintenance duration).
They are applied on the client: `--template` on `create`, `schedule-maintenance` and `updates add`
fills in values that weren't passed explicitly.
"""

import re
from typing import Any, Dict, List, Optional

import typer
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from .base import BaseCommand, to_plain
from .status_page_common import COMPONENT_STATUSES, INCIDENT_STATUSES, styled, text, truncate
from ..utils.time_utils import format_dt

TEMPLATE_TYPES = ("incident", "maintenance")
MAX_DURATION_MINUTES = 43200
_DURATION = re.compile(r"^(?:(\d+)d)?\s*(?:(\d+)h)?\s*(?:(\d+)m)?$")


def parse_duration(value: Optional[str], option: str = "--duration") -> Optional[int]:
    """Parse '90', '90m', '2h', '1h30m' or '1d' into minutes."""
    if value is None:
        return None
    raw = value.strip().lower()
    if raw.isdigit():
        minutes = int(raw)
    else:
        match = _DURATION.match(raw)
        if not raw or not match or not any(match.groups()):
            raise typer.BadParameter(f"'{value}' must be minutes or like 90m, 2h, 1h30m, 1d", param_hint=option)
        days, hours, mins = (int(g or 0) for g in match.groups())
        minutes = days * 1440 + hours * 60 + mins
    if not 1 <= minutes <= MAX_DURATION_MINUTES:
        raise typer.BadParameter(f"must be between 1 minute and {MAX_DURATION_MINUTES // 1440} days", param_hint=option)
    return minutes


def format_minutes(minutes: Optional[int]) -> str:
    if not minutes:
        return "-"
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h{mins}m"
    return f"{hours}h" if hours else f"{mins}m"


def parse_template_components(values: Optional[List[str]], template_type: str,
                              option: str = "--component") -> Optional[Dict[str, str]]:
    """Parse repeated -c options: ID=STATUS for incident templates, ID (or ID=STATUS) for maintenance."""
    if not values:
        return None
    result: Dict[str, str] = {}
    for raw in values:
        sep = "=" if "=" in raw else ":" if ":" in raw else None
        component_id, status = ((p.strip() for p in raw.split(sep, 1)) if sep else (raw.strip(), ""))
        if not component_id:
            raise typer.BadParameter(f"'{raw}' must look like COMPONENT_ID=STATUS", param_hint=option)
        if template_type == "maintenance":
            result[component_id] = "under_maintenance"
            continue
        if status not in COMPONENT_STATUSES:
            raise typer.BadParameter(
                f"'{raw}': incident templates need COMPONENT_ID=STATUS with STATUS one of {', '.join(COMPONENT_STATUSES)}",
                param_hint=option,
            )
        result[component_id] = status
    return result


class IncidentTemplatesCommand(BaseCommand):
    """Reusable incident and maintenance templates of a status page"""

    def _api(self):
        from pingera.api import StatusPagesIncidentTemplatesApi
        return self.api(StatusPagesIncidentTemplatesApi)

    def fetch(self, page_id: str, template_id: str):
        try:
            return self._api().v1_pages_page_id_incident_templates_template_id_get(
                page_id=page_id, template_id=template_id
            )
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get incident template", e)

    def list_templates(self, page_id: str, template_type: Optional[str]):
        try:
            templates = self._api().v1_pages_page_id_incident_templates_get(page_id=page_id, type=template_type) or []
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("list incident templates", e)

        if self.machine_output:
            self.output_model(templates)
            return
        if not templates:
            self.display_info(f"Page {page_id} has no {template_type or 'incident or maintenance'} templates.\n"
                              f"Create one: pngr pages incidents templates create -p {page_id} --type incident "
                              "--name NAME --title TITLE")
            return

        table = Table(title=f"Templates of page {page_id}", header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Type")
        table.add_column("Name", style="green")
        table.add_column("Title")
        table.add_column("Status")
        table.add_column("Duration")
        table.add_column("Components", justify="right")
        table.add_column("Message")
        for tpl in templates:
            table.add_row(
                text(tpl.id), text(tpl.type), text(tpl.name), truncate(tpl.title, 40), styled(tpl.status),
                format_minutes(tpl.duration_minutes), str(len(tpl.components or {})) if tpl.components else "-",
                truncate(tpl.body, 50),
            )
        self.console.print(table)
        self.console.print(f"[dim]{len(templates)} template(s) • max 50 per page[/dim]")

    def show_template(self, page_id: str, template_id: str):
        tpl = self.fetch(page_id, template_id)
        if self.machine_output:
            self.output_model(tpl)
            return
        lines = [
            f"[bold]ID:[/bold] {text(tpl.id)}",
            f"[bold]Type:[/bold] {text(tpl.type)}",
            f"[bold]Title:[/bold] {text(tpl.title)}",
        ]
        if tpl.type == "incident":
            lines.append(f"[bold]Status:[/bold] {styled(tpl.status) if tpl.status else '[dim]not changed[/dim]'}")
        else:
            lines.append(f"[bold]Duration:[/bold] {format_minutes(tpl.duration_minutes)}")
        if tpl.components:
            lines.append("[bold]Components:[/bold]")
            lines.extend(f"  • {cid}: {styled(status)}" for cid, status in tpl.components.items())
        lines.append(f"[bold]Updated:[/bold] {format_dt(tpl.updated_at)} UTC")
        lines.append("")
        lines.append(text(tpl.body, "[dim](empty message)[/dim]"))
        self.console.print(Panel("\n".join(lines), title=f"📄 {text(tpl.name)}", border_style="cyan", padding=(1, 2)))

    def create_template(self, page_id: str, payload: Dict[str, Any]):
        try:
            tpl = self._api().v1_pages_page_id_incident_templates_post(page_id=page_id, incident_template=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("create incident template", e)

        if self.machine_output:
            self.output_model(tpl)
            return
        flag = "pngr pages incidents create" if tpl.type == "incident" else "pngr pages incidents schedule-maintenance"
        self.display_success(
            f"ID: {text(tpl.id)}\nName: {text(tpl.name)}\nType: {text(tpl.type)}\n"
            f"Use it: {flag} -p {page_id} --template {text(tpl.id)}",
            "✅ Template Created",
        )

    def update_template(self, page_id: str, template_id: str, payload: Dict[str, Any]):
        try:
            tpl = self._api().v1_pages_page_id_incident_templates_template_id_patch(
                page_id=page_id, template_id=template_id, incident_template1=payload
            )
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("update incident template", e)

        if self.machine_output:
            self.output_model(tpl)
            return
        changed = ", ".join(k.replace("_", " ") for k in payload)
        self.display_success(f"ID: {text(tpl.id, template_id)}\nChanged: {changed}", "✅ Template Updated")

    def delete_template(self, page_id: str, template_id: str, confirm: bool):
        if not confirm and not Confirm.ask(f"Delete template {template_id}?", console=self.error_console):
            self.error_console.print("[yellow]Operation cancelled.[/yellow]")
            return
        try:
            self._api().v1_pages_page_id_incident_templates_template_id_delete(page_id=page_id, template_id=template_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("delete incident template", e)

        if self.machine_output:
            self.output_data({"deleted": True, "id": template_id})
        else:
            self.display_success(f"Template {template_id} deleted.", "✅ Template Deleted")

    def existing_component_ids(self, page_id: str) -> Optional[set]:
        """IDs of the page's current components, or None if they can't be listed."""
        from pingera.api import StatusPagesComponentsApi
        try:
            components = self.api(StatusPagesComponentsApi).v1_pages_page_id_components_get(page_id=page_id) or []
        except Exception:
            return None
        return {c.id for c in components if getattr(c, "id", None)}

    def load_for(self, page_id: str, template_id: str, expected_type: str) -> Dict[str, Any]:
        """Fetch a template for applying it; components deleted since it was saved are dropped."""
        tpl = self.fetch(page_id, template_id)
        if tpl.type != expected_type:
            raise typer.BadParameter(
                f"template {template_id} is a {tpl.type} template; use a {expected_type} template",
                param_hint="--template",
            )
        data = to_plain(tpl)
        components = data.get("components") or {}
        if components:
            existing = self.existing_component_ids(page_id)
            if existing is not None:
                skipped = [cid for cid in components if cid not in existing]
                components = {cid: st for cid, st in components.items() if cid in existing}
                if skipped:
                    self.error_console.print(
                        f"[yellow]Skipping components from the template that no longer exist: {', '.join(skipped)}[/yellow]"
                    )
        data["components"] = components or None
        return data


def load_template(page_id: str, template_id: Optional[str], expected_type: str) -> Optional[Dict[str, Any]]:
    """Template values for `--template`, or None when no template was given."""
    if not template_id:
        return None
    from ..utils.config import get_output_format
    return IncidentTemplatesCommand(get_output_format()).load_for(page_id, template_id, expected_type)


TEMPLATE_OPTION_HELP = (
    "Template ID to start from (see 'pngr pages incidents templates list'). "
    "Options passed explicitly override the template's values"
)

app = typer.Typer(
    name="templates",
    help="📄 Manage reusable incident and maintenance templates",
    no_args_is_help=True,
)

PAGE_ID = typer.Option(..., "--page-id", "-p", help="Status page ID")
TEMPLATE_ID = typer.Argument(..., help="Template ID")
COMPONENT_HELP = (
    "Component to pre-select (repeatable). Incident templates: ID=STATUS "
    f"(STATUS: {', '.join(COMPONENT_STATUSES)}); maintenance templates: ID"
)


def _output_format():
    from ..utils.config import get_output_format
    return get_output_format()


def _check_type(value: Optional[str]):
    if value is not None and value not in TEMPLATE_TYPES:
        raise typer.BadParameter(f"must be one of {', '.join(TEMPLATE_TYPES)}", param_hint="--type")


def _check_status(value: Optional[str]):
    if value is not None and value not in INCIDENT_STATUSES:
        raise typer.BadParameter(f"must be one of {', '.join(INCIDENT_STATUSES)}", param_hint="--status")


def _check_text(name: Optional[str], title: Optional[str]):
    if name is not None and not 1 <= len(name.strip()) <= 100:
        raise typer.BadParameter("must be 1-100 characters", param_hint="--name")
    if title is not None and not 1 <= len(title.strip()) <= 200:
        raise typer.BadParameter("must be 1-200 characters", param_hint="--title")


@app.command("list")
def list_templates(
    page_id: str = PAGE_ID,
    template_type: Optional[str] = typer.Option(None, "--type", "-t", help="Only incident or maintenance templates"),
):
    """List a page's incident and maintenance templates"""
    _check_type(template_type)
    IncidentTemplatesCommand(_output_format()).list_templates(page_id, template_type)


@app.command("get")
def get_template(template_id: str = TEMPLATE_ID, page_id: str = PAGE_ID):
    """Show a template with its full message"""
    IncidentTemplatesCommand(_output_format()).show_template(page_id, template_id)


@app.command("create")
def create_template(
    page_id: str = PAGE_ID,
    template_type: str = typer.Option(..., "--type", "-t", help="incident or maintenance"),
    name: str = typer.Option(..., "--name", "-n", help="Label shown in the template list, e.g. 'DB outage - investigating' (max 100)"),
    title: str = typer.Option(..., "--title", help="Incident or maintenance title the template fills in (max 200)"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Message the template fills in"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help=f"Incident templates only: {', '.join(INCIDENT_STATUSES)}"),
    component: Optional[List[str]] = typer.Option(None, "--component", "-c", help=COMPONENT_HELP),
    duration: Optional[str] = typer.Option(None, "--duration", "-d", help="Maintenance templates only: window length, e.g. 90m, 2h, 1h30m"),
):
    """Create an incident or maintenance template (max 50 per page)"""
    _check_type(template_type)
    _check_text(name, title)
    _check_status(status)
    if template_type == "maintenance" and status is not None:
        raise typer.BadParameter("maintenance templates can't set an incident status", param_hint="--status")
    if template_type == "incident" and duration is not None:
        raise typer.BadParameter("only maintenance templates have a duration", param_hint="--duration")
    payload: Dict[str, Any] = {"type": template_type, "name": name.strip(), "title": title.strip()}
    if body is not None:
        payload["body"] = body
    if status is not None:
        payload["status"] = status
    components = parse_template_components(component, template_type)
    if components:
        payload["components"] = components
    minutes = parse_duration(duration)
    if minutes:
        payload["duration_minutes"] = minutes
    IncidentTemplatesCommand(_output_format()).create_template(page_id, payload)


@app.command("update")
def update_template(
    template_id: str = TEMPLATE_ID,
    page_id: str = PAGE_ID,
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New label"),
    title: Optional[str] = typer.Option(None, "--title", help="New title"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="New message"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help=f"Incident templates: {', '.join(INCIDENT_STATUSES)}"),
    clear_status: bool = typer.Option(False, "--clear-status", help="Don't change the incident status when applied"),
    component: Optional[List[str]] = typer.Option(None, "--component", "-c", help=COMPONENT_HELP + ". Replaces the template's components"),
    clear_components: bool = typer.Option(False, "--clear-components", help="Remove all pre-selected components"),
    duration: Optional[str] = typer.Option(None, "--duration", "-d", help="Maintenance templates: new window length, e.g. 2h"),
    clear_duration: bool = typer.Option(False, "--clear-duration", help="Remove the default duration"),
):
    """Update a template; only the options you pass are changed"""
    if status and clear_status:
        raise typer.BadParameter("use either --status or --clear-status", param_hint="--clear-status")
    if component and clear_components:
        raise typer.BadParameter("use either --component or --clear-components", param_hint="--clear-components")
    if duration and clear_duration:
        raise typer.BadParameter("use either --duration or --clear-duration", param_hint="--clear-duration")
    _check_text(name, title)
    _check_status(status)
    payload: Dict[str, Any] = {}
    if name is not None:
        payload["name"] = name.strip()
    if title is not None:
        payload["title"] = title.strip()
    if body is not None:
        payload["body"] = body
    if status is not None:
        payload["status"] = status
    if clear_status:
        payload["status"] = None
    if clear_components:
        payload["components"] = None
    if duration is not None:
        payload["duration_minutes"] = parse_duration(duration)
    if clear_duration:
        payload["duration_minutes"] = None
    command = IncidentTemplatesCommand(_output_format())
    if component:
        # Component syntax depends on the template type, which only the server knows
        current = command.fetch(page_id, template_id)
        payload["components"] = parse_template_components(component, current.type)
    if not payload:
        raise typer.BadParameter(
            "nothing to update: pass --name, --title, --body, --status, --component, --duration or a --clear-* option",
            param_hint="--name",
        )
    command.update_template(page_id, template_id, payload)


@app.command("delete")
def delete_template(
    template_id: str = TEMPLATE_ID,
    page_id: str = PAGE_ID,
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """Delete a template (incidents created from it are not affected)"""
    IncidentTemplatesCommand(_output_format()).delete_template(page_id, template_id, confirm)
