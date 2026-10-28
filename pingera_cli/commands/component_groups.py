"""
Component group commands: `pngr pages component-groups ...`
"""

from typing import Any, Dict, List, Optional

import typer
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from .base import BaseCommand, to_plain
from .status_page_common import styled, text, truncate
from ..utils.time_utils import format_dt


class ComponentGroupsCommand(BaseCommand):
    """Manage component groups (components that act as containers for other components)"""

    def _api(self):
        from pingera.api import StatusPagesComponentsApi
        return self.api(StatusPagesComponentsApi)

    def _children(self, api, page_id: str) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """Map group_id -> member components (the API doesn't return members); None if unavailable."""
        try:
            components = api.v1_pages_page_id_components_get(page_id=page_id, show_groups=False) or []
        except Exception:
            return None
        children: Dict[str, List[Dict[str, Any]]] = {}
        for comp in components:
            if comp.group_id and not comp.group:
                children.setdefault(str(comp.group_id), []).append(
                    {"id": comp.id, "name": comp.name, "status": comp.status}
                )
        return children

    def list_groups(self, page_id: str):
        try:
            api = self._api()
            groups = api.v1_pages_page_id_component_groups_get(page_id=page_id) or []
            children = self._children(api, page_id) if groups else {}
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("list component groups", e)

        if self.machine_output:
            data = []
            for group in groups:
                item = to_plain(group)
                if children is not None:
                    item["components"] = children.get(str(group.id), [])
                data.append(item)
            self.output_data(data)
            return

        if not groups:
            self.display_info(f"No component groups on page {page_id}.\n"
                              f"Create one: pngr pages component-groups create --page-id {page_id} --name NAME")
            return

        table = Table(title=f"Component groups: {page_id}", header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Components")
        table.add_column("Position", justify="right")
        table.add_column("Description")
        for group in groups:
            members = None if children is None else children.get(str(group.id), [])
            if members is None:
                members_text = "?"
            elif not members:
                members_text = "[dim]none[/dim]"
            else:
                members_text = f"{len(members)}: " + truncate(", ".join(text(m.get("name")) for m in members), 50)
            table.add_row(text(group.id), text(group.name), members_text, text(group.position), truncate(group.description, 40))
        self.console.print(table)
        self.console.print(f"[dim]{len(groups)} group(s) • details: pngr pages component-groups get <group-id> --page-id {page_id}[/dim]")

    def get_group(self, page_id: str, group_id: str):
        try:
            api = self._api()
            group = api.v1_pages_page_id_component_groups_component_id_get(page_id=page_id, component_id=group_id)
            children = self._children(api, page_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("get component group", e)

        members = None if children is None else children.get(str(group.id or group_id), [])
        if self.machine_output:
            data = to_plain(group)
            if members is not None:
                data["components"] = members
            self.output_data(data)
            return

        body = (
            f"[bold cyan]ID:[/bold cyan] {text(group.id)}\n"
            f"[bold cyan]Name:[/bold cyan] {text(group.name)}\n"
            f"[bold cyan]Description:[/bold cyan] {text(group.description)}\n"
            f"[bold cyan]Position:[/bold cyan] {text(group.position)}\n"
            f"[bold cyan]Created:[/bold cyan] {format_dt(group.created_at)}  "
            f"[bold cyan]Updated:[/bold cyan] {format_dt(group.updated_at)}"
        )
        self.console.print(Panel(body, title=f"🗂  Component group: {text(group.name)}", border_style="blue", padding=(1, 2)))
        if members is None:
            self.display_warning("Could not load the page's components to show group members.")
        elif not members:
            self.console.print("[dim]No components in this group. Add some: "
                               f"pngr pages component-groups update {group_id} --page-id {page_id} --add-component ID[/dim]")
        else:
            table = Table(title="Components in group", header_style="bold magenta")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="green")
            table.add_column("Status")
            for member in members:
                table.add_row(text(member.get("id")), text(member.get("name")), styled(member.get("status")))
            self.console.print(table)

    def _set_membership(self, api, page_id: str, component_ids: List[str], group_id: Optional[str]) -> Dict[str, str]:
        """PATCH each component's group_id; returns {component_id: error} for the ones that failed."""
        from .base import format_api_error

        errors: Dict[str, str] = {}
        for component_id in component_ids:
            try:
                api.v1_pages_page_id_components_component_id_patch(
                    page_id=page_id, component_id=component_id, component1={"group_id": group_id}
                )
            except Exception as e:
                errors[component_id] = format_api_error(e)
        return errors

    def create_group(self, page_id: str, name: str, description: Optional[str], position: Optional[int],
                     component_ids: List[str]):
        payload: Dict[str, Any] = {"name": name, "group": True}
        if description is not None:
            payload["description"] = description
        if position is not None:
            payload["position"] = position
        try:
            api = self._api()
            group = api.v1_pages_page_id_component_groups_post(page_id=page_id, component=payload)
            errors = self._set_membership(api, page_id, component_ids, group.id) if component_ids else {}
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("create component group", e)

        if self.machine_output:
            self.output_model(group)
        else:
            details = f"ID: {group.id}\nName: {text(group.name)}"
            if component_ids:
                details += f"\nComponents added: {len(component_ids) - len(errors)} of {len(component_ids)}"
            self.display_success(details, "✅ Component Group Created")
        self._report_membership_errors(errors)

    def update_group(self, page_id: str, group_id: str, name: Optional[str], description: Optional[str],
                     position: Optional[int], add: List[str], remove: List[str]):
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if position is not None:
            payload["position"] = position
        if not payload and not add and not remove:
            raise typer.BadParameter("nothing to update: pass --name, --description, --position, --add-component or --remove-component")
        try:
            api = self._api()
            group = None
            if payload:
                group = api.v1_pages_page_id_component_groups_component_id_patch(
                    page_id=page_id, component_id=group_id, component1=payload
                )
            add_errors = self._set_membership(api, page_id, add, group_id) if add else {}
            remove_errors = self._set_membership(api, page_id, remove, None) if remove else {}
            errors = {**add_errors, **remove_errors}
            if group is None and self.machine_output:
                group = api.v1_pages_page_id_component_groups_component_id_get(page_id=page_id, component_id=group_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("update component group", e)

        if self.machine_output:
            self.output_model(group)
        else:
            lines = [f"ID: {group_id}"]
            if payload:
                lines.append("Updated: " + ", ".join(payload))
            if add:
                lines.append(f"Components added: {len(add) - len(add_errors)} of {len(add)}")
            if remove:
                lines.append(f"Components removed: {len(remove) - len(remove_errors)} of {len(remove)}")
            self.display_success("\n".join(lines), "✅ Component Group Updated")
        self._report_membership_errors(errors)

    def _report_membership_errors(self, errors: Dict[str, str]):
        if errors:
            self.display_error("Some components could not be moved:\n" +
                               "\n".join(f"{cid}: {msg}" for cid, msg in errors.items()))
            raise typer.Exit(1)

    def delete_group(self, page_id: str, group_id: str, confirm: bool):
        if not confirm and not Confirm.ask(
            f"Delete component group {group_id}? Its components are kept but become ungrouped.",
            console=self.error_console,
        ):
            self.error_console.print("[yellow]Operation cancelled.[/yellow]")
            return
        try:
            self._api().v1_pages_page_id_component_groups_component_id_delete(page_id=page_id, component_id=group_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("delete component group", e)

        if self.machine_output:
            self.output_data({"deleted": True, "id": group_id})
        else:
            self.display_success(f"Component group {group_id} deleted. Its components are now ungrouped.",
                                 "✅ Component Group Deleted")


app = typer.Typer(name="component-groups", help="🗂  Manage component groups on a status page", no_args_is_help=True)

PAGE_ID = typer.Option(..., "--page-id", "-p", help="Status page ID")


@app.command("list")
def list_groups(page_id: str = PAGE_ID):
    """List component groups with the components they contain"""
    from ..utils.config import get_output_format
    ComponentGroupsCommand(get_output_format()).list_groups(page_id)


@app.command("get")
def get_group(
    group_id: str = typer.Argument(..., help="Component group ID"),
    page_id: str = PAGE_ID,
):
    """Show a component group and its member components"""
    from ..utils.config import get_output_format
    ComponentGroupsCommand(get_output_format()).get_group(page_id, group_id)


@app.command("create")
def create_group(
    page_id: str = PAGE_ID,
    name: str = typer.Option(..., "--name", "-n", help="Group name (1-100 characters)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Group description"),
    position: Optional[int] = typer.Option(None, "--position", help="Display order on the status page"),
    component_ids: Optional[List[str]] = typer.Option(None, "--component-id", "-c", help="Existing component to move into the group (repeatable)"),
):
    """Create a component group, optionally moving existing components into it"""
    if len(name) > 100:
        raise typer.BadParameter("must be at most 100 characters", param_hint="--name")
    from ..utils.config import get_output_format
    ComponentGroupsCommand(get_output_format()).create_group(page_id, name, description, position, component_ids or [])


@app.command("update")
def update_group(
    group_id: str = typer.Argument(..., help="Component group ID"),
    page_id: str = PAGE_ID,
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New group name (1-100 characters)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    position: Optional[int] = typer.Option(None, "--position", help="Display order on the status page"),
    add: Optional[List[str]] = typer.Option(None, "--add-component", help="Component ID to move into the group (repeatable)"),
    remove: Optional[List[str]] = typer.Option(None, "--remove-component", help="Component ID to take out of the group (repeatable)"),
):
    """Update a component group (PATCH) and/or change which components belong to it"""
    if name is not None and not 1 <= len(name) <= 100:
        raise typer.BadParameter("must be 1-100 characters", param_hint="--name")
    from ..utils.config import get_output_format
    ComponentGroupsCommand(get_output_format()).update_group(page_id, group_id, name, description, position, add or [], remove or [])


@app.command("delete")
def delete_group(
    group_id: str = typer.Argument(..., help="Component group ID"),
    page_id: str = PAGE_ID,
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """Delete a component group (member components are kept and become ungrouped)"""
    from ..utils.config import get_output_format
    ComponentGroupsCommand(get_output_format()).delete_group(page_id, group_id, confirm)
