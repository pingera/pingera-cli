"""
Custom sender email domain commands: `pngr pages email-domain show|setup|verify`
"""

from typing import Any, Dict, Optional

import typer
from rich.panel import Panel
from rich.table import Table

from .base import BaseCommand
from .status_page_common import text

_RECORD_ORDER = ("verification", "dkim", "spf", "dmarc")
_RECORD_PURPOSE = {
    "verification": "Domain ownership",
    "dkim": "DKIM signature",
    "spf": "SPF (allowed senders)",
    "dmarc": "DMARC",
}


class EmailDomainCommand(BaseCommand):
    """Send subscriber notifications from your own email domain"""

    def _api(self):
        from pingera.api import StatusPagesApi
        return self.api(StatusPagesApi)

    def _call(self, action: str, method: str, page_id: str, before=None):
        try:
            api = self._api()
            if before:
                before(api)
            return getattr(api, method)(page_id=page_id)
        except typer.Exit:
            raise
        except Exception as e:
            self.fail(action, e)

    def show(self, page_id: str):
        data = self._call("get email domain", "v1_pages_page_id_email_domain_get", page_id)
        if self.machine_output:
            self.output_model(data)
            return
        self._render(page_id, data)
        if not data.email_domain:
            self.console.print(f"[dim]💡 Set a sender address and register it: "
                               f"pngr pages email-domain setup --page-id {page_id} --from-email noreply@example.com[/dim]")
        elif not data.dns_records:
            self.console.print(f"[dim]💡 Register the domain to get DNS records: pngr pages email-domain setup --page-id {page_id}[/dim]")
        elif not data.email_domain_verified:
            self.console.print(f"[dim]💡 After adding the records: pngr pages email-domain verify --page-id {page_id}[/dim]")

    def setup(self, page_id: str, from_email: Optional[str], from_name: Optional[str]):
        page_changes: Dict[str, Any] = {}
        if from_email is not None:
            page_changes["notifications_from_email"] = from_email
        if from_name is not None:
            page_changes["notifications_from_name"] = from_name

        def update_page(api):
            if page_changes:
                api.v1_pages_page_id_patch(page_id=page_id, page1=page_changes)

        data = self._call("set up email domain", "v1_pages_page_id_email_domain_records_post", page_id, before=update_page)
        if self.machine_output:
            self.output_model(data)
            return
        self.display_success(f"Domain {text(data.email_domain)} registered with the mail provider.\n"
                             "Add the DNS records below, then run "
                             f"'pngr pages email-domain verify --page-id {page_id}'.", "✅ Email Domain Registered")
        self._render(page_id, data)

    def verify(self, page_id: str):
        data = self._call("verify email domain", "v1_pages_page_id_email_domain_verify_post", page_id)
        if self.machine_output:
            self.output_model(data)
            return
        if data.email_domain_verified:
            self.display_success(f"{text(data.email_domain)} is verified. Notifications are sent from "
                                 f"{text(data.notifications_from_email)}.", "✅ Email Domain Verified")
        else:
            self.display_warning(f"{text(data.email_domain)} is not verified yet "
                                 f"(status: {text(data.email_domain_status)}). DNS changes can take a while "
                                 "to propagate; check the records below and try again later.")
            self._render(page_id, data)

    def _render(self, page_id: str, data):
        verified = data.email_domain_verified
        if not data.email_domain:
            state = "[dim]not configured[/dim]"
        elif verified:
            state = "[green]✓ verified[/green]"
        else:
            state = f"[yellow]{text(data.email_domain_status, 'not registered')}[/yellow]"
        info = (
            f"[bold cyan]Sender email:[/bold cyan] {text(data.notifications_from_email)}\n"
            f"[bold cyan]Sender name:[/bold cyan] {text(data.notifications_from_name)}\n"
            f"[bold cyan]Domain:[/bold cyan] {text(data.email_domain)}\n"
            f"[bold cyan]Status:[/bold cyan] {state}"
        )
        self.console.print(Panel(info, title=f"✉️  Sender email domain: page {page_id}", border_style="blue", padding=(1, 2)))

        dns = data.dns_records
        records = {key: getattr(dns, key) for key in _RECORD_ORDER if dns and getattr(dns, key)}
        if not records:
            return
        table = Table(title="DNS records to create", header_style="bold magenta", show_lines=True)
        table.add_column("Purpose")
        table.add_column("Type", style="cyan")
        table.add_column("Name / Host", style="green", overflow="fold")
        table.add_column("Value", overflow="fold")
        for key, record in records.items():
            table.add_row(_RECORD_PURPOSE[key], text(record.type), text(record.name), text(record.value))
        self.console.print(table)


app = typer.Typer(name="email-domain", help="✉️  Send notifications from your own email domain", no_args_is_help=True)

PAGE_ID = typer.Option(..., "--page-id", "-p", help="Status page ID")


def _output_format():
    from ..utils.config import get_output_format
    return get_output_format()


@app.command("show")
def show(page_id: str = PAGE_ID):
    """Show the sender domain, its verification status and the DNS records to create"""
    EmailDomainCommand(_output_format()).show(page_id)


@app.command("setup")
def setup(
    page_id: str = PAGE_ID,
    from_email: Optional[str] = typer.Option(None, "--from-email", help="Sender address to use (sets the page's notifications_from_email first); its domain is registered"),
    from_name: Optional[str] = typer.Option(None, "--from-name", help="Sender display name (max 100)"),
):
    """Register the sender email's domain with the mail provider and print the DNS records to add"""
    if from_email is not None and ("@" not in from_email or not from_email.split("@", 1)[1]):
        raise typer.BadParameter("must be an email address", param_hint="--from-email")
    if from_name is not None and len(from_name) > 100:
        raise typer.BadParameter("must be at most 100 characters", param_hint="--from-name")
    EmailDomainCommand(_output_format()).setup(page_id, from_email, from_name)


@app.command("verify")
def verify(page_id: str = PAGE_ID):
    """Check the DNS records with the mail provider and refresh the verification status"""
    EmailDomainCommand(_output_format()).verify(page_id)
