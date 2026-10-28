"""
Status page password commands: `pngr pages passwords ...`
"""

from typing import Any, Dict, Optional

import click
import typer
from rich.prompt import Confirm
from rich.table import Table

from .base import BaseCommand
from .status_page_common import as_dict, as_list, iso, parse_future_time, raw_json, text
from ..utils.time_utils import format_dt


class PagePasswordsCommand(BaseCommand):
    """Manage the passwords visitors use to open a password-protected status page"""

    def _api(self):
        from pingera.api import PagePasswordsApi
        return self.api(PagePasswordsApi)

    def list_passwords(self, page_id: str):
        try:
            data = raw_json(self._api(), "v1_pages_page_id_passwords_get", page_id=page_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("list page passwords", e)

        passwords = [as_dict(p) for p in as_list(data)]
        if self.machine_output:
            self.output_data(passwords)
            return
        if not passwords:
            self.display_info(f"Page {page_id} has no passwords (it is not password protected).\n"
                              f"Add one: pngr pages passwords add --page-id {page_id} --name NAME")
            return

        table = Table(title=f"Passwords of page {page_id}", header_style="bold magenta")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Hint")
        table.add_column("State")
        table.add_column("Expires (UTC)")
        table.add_column("Created (UTC)")
        for pw in passwords:
            if pw.get("is_expired") is True:
                state = "[red]expired[/red]"
            elif pw.get("active") is False:
                state = "[yellow]inactive[/yellow]"
            else:
                state = "[green]active[/green]"
            table.add_row(
                text(pw.get("id")), text(pw.get("name")), text(pw.get("password_hint")), state,
                format_dt(pw.get("expires_at")) if pw.get("expires_at") else "[dim]never[/dim]",
                format_dt(pw.get("created_at")),
            )
        self.console.print(table)
        self.console.print(f"[dim]{len(passwords)} password(s) • max 10 per page[/dim]")

    def add_password(self, page_id: str, payload: Dict[str, Any]):
        try:
            data = raw_json(self._api(), "v1_pages_page_id_passwords_post", page_id=page_id, page_password_create=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("add page password", e)

        pw = as_dict(data)
        if self.machine_output:
            self.output_data(pw)
            return
        lines = [f"ID: {text(pw.get('id'))}", f"Name: {text(pw.get('name') or payload.get('name'), '(unnamed)')}"]
        if payload.get("expires_at"):
            lines.append(f"Expires: {format_dt(payload['expires_at'])} UTC")
        lines.append("Password protection is now enabled for the page.")
        self.display_success("\n".join(lines), "✅ Password Added")

    def update_password(self, page_id: str, password_id: str, payload: Dict[str, Any]):
        try:
            data = raw_json(self._api(), "v1_pages_page_id_passwords_password_id_put",
                            page_id=page_id, password_id=password_id, page_password_update=payload)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("update page password", e)

        pw = as_dict(data)
        if self.machine_output:
            self.output_data(pw)
            return
        changed = ", ".join("password" if k == "password" else k.replace("_", " ") for k in payload)
        self.display_success(f"ID: {text(pw.get('id'), password_id)}\nChanged: {changed}", "✅ Password Updated")

    def delete_password(self, page_id: str, password_id: str, confirm: bool):
        if not confirm and not Confirm.ask(
            f"Delete password {password_id}? Visitors using it lose access "
            "(deleting the last password turns off password protection).",
            console=self.error_console,
        ):
            self.error_console.print("[yellow]Operation cancelled.[/yellow]")
            return
        try:
            self._api().v1_pages_page_id_passwords_password_id_delete(page_id=page_id, password_id=password_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail("delete page password", e)

        if self.machine_output:
            self.output_data({"deleted": True, "id": password_id})
        else:
            self.display_success(f"Password {password_id} deleted.", "✅ Password Deleted")


app = typer.Typer(name="passwords", help="🔑 Manage passwords of password-protected status pages", no_args_is_help=True)

PAGE_ID = typer.Option(..., "--page-id", "-p", help="Status page ID")


def _check_password(value: str, option: str = "--password"):
    if len(value) < 8:
        raise typer.BadParameter("must be at least 8 characters", param_hint=option)


def _check_lengths(name: Optional[str], hint: Optional[str]):
    if name is not None and len(name) > 100:
        raise typer.BadParameter("must be at most 100 characters", param_hint="--name")
    if hint is not None and len(hint) > 200:
        raise typer.BadParameter("must be at most 200 characters", param_hint="--hint")


def _expiry(value: Optional[str]) -> Optional[str]:
    parsed = parse_future_time(value, "--expires")
    if parsed is not None:
        from datetime import datetime, timezone
        if parsed <= datetime.now(timezone.utc):
            raise typer.BadParameter("must be in the future", param_hint="--expires")
    return iso(parsed)


def _output_format():
    from ..utils.config import get_output_format
    return get_output_format()


@app.command("list")
def list_passwords(page_id: str = PAGE_ID):
    """List page passwords with their hints, state and expiry (passwords themselves are never shown)"""
    PagePasswordsCommand(_output_format()).list_passwords(page_id)


@app.command("add")
def add_password(
    page_id: str = PAGE_ID,
    password: Optional[str] = typer.Option(None, "--password", help="The password (min 8 characters). Prompted (hidden) if omitted"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Label to tell passwords apart, e.g. a customer name (max 100)"),
    hint: Optional[str] = typer.Option(None, "--hint", help="Hint shown to visitors on the password prompt (max 200)"),
    expires: Optional[str] = typer.Option(None, "--expires", help="Expiry time (ISO 8601 or +30d from now). Default: never"),
):
    """Add a password (enables password protection on the page; max 10 passwords)"""
    _check_lengths(name, hint)
    expires_at = _expiry(expires)
    if password is None:
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True, err=True)
    _check_password(password)
    payload: Dict[str, Any] = {"password": password}
    if name is not None:
        payload["name"] = name
    if hint is not None:
        payload["password_hint"] = hint
    if expires_at:
        payload["expires_at"] = expires_at
    PagePasswordsCommand(_output_format()).add_password(page_id, payload)


@app.command("update")
def update_password(
    password_id: str = typer.Argument(..., help="Password ID"),
    page_id: str = PAGE_ID,
    password: Optional[str] = typer.Option(None, "--password", help="New password (min 8 characters)"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New label"),
    hint: Optional[str] = typer.Option(None, "--hint", help="New hint shown to visitors"),
    active: Optional[bool] = typer.Option(None, "--active/--inactive", help="Enable or disable this password"),
    expires: Optional[str] = typer.Option(None, "--expires", help="New expiry (ISO 8601 or +30d from now)"),
    no_expiry: bool = typer.Option(False, "--no-expiry", help="Remove the expiry date"),
):
    """Update a password's value, label, hint, state or expiry"""
    if expires and no_expiry:
        raise typer.BadParameter("use either --expires or --no-expiry", param_hint="--no-expiry")
    _check_lengths(name, hint)
    payload: Dict[str, Any] = {}
    if password is not None:
        _check_password(password)
        payload["password"] = password
    if name is not None:
        payload["name"] = name
    if hint is not None:
        payload["password_hint"] = hint
    if active is not None:
        payload["active"] = active
    if expires is not None:
        payload["expires_at"] = _expiry(expires)
    if no_expiry:
        payload["expires_at"] = None
    if not payload:
        raise typer.BadParameter("nothing to update: pass --password, --name, --hint, --active/--inactive, --expires or --no-expiry",
                                 param_hint="--name")
    PagePasswordsCommand(_output_format()).update_password(page_id, password_id, payload)


@app.command("delete")
def delete_password(
    password_id: str = typer.Argument(..., help="Password ID"),
    page_id: str = PAGE_ID,
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """Delete a password (removing the last one turns password protection off)"""
    PagePasswordsCommand(_output_format()).delete_password(page_id, password_id, confirm)
