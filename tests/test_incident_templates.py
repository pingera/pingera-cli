"""
Tests for incident/maintenance templates: `pngr pages incidents templates ...` and `--template` on
`create`, `schedule-maintenance` and `updates add`
"""

import json

import pytest
from pingera.models import Component, Incident, IncidentTemplate

from pingera_cli.commands.incident_templates import parse_duration
from pingera_cli.commands.incidents import IncidentsCommand
from pingera_cli.main import app


@pytest.fixture(autouse=True)
def wide_console():
    from pingera_cli.utils.console import console
    previous = console._width
    console.width = 200
    yield
    console._width = previous


@pytest.fixture
def tpls(sdk_apis):
    return sdk_apis["StatusPagesIncidentTemplatesApi"]


@pytest.fixture
def incs(sdk_apis, monkeypatch):
    api = sdk_apis["StatusPagesIncidentsApi"]
    monkeypatch.setattr(IncidentsCommand, "get_client", lambda self: api)
    return api


@pytest.fixture
def comps(sdk_apis):
    api = sdk_apis["StatusPagesComponentsApi"]
    api.v1_pages_page_id_components_get.return_value = [Component(id="c1", name="API"), Component(id="c2", name="Web")]
    return api


INCIDENT_TPL = IncidentTemplate(
    id="t1", page_id="pg1", type="incident", name="API down", title="API is unavailable",
    body="We are investigating.", status="investigating", components={"c1": "major_outage", "gone": "partial_outage"},
)
RESOLVED_TPL = IncidentTemplate(
    id="t2", page_id="pg1", type="incident", name="Resolved", title="Resolved",
    body="All good now.", status="resolved", components={"c1": "operational"},
)
MAINT_TPL = IncidentTemplate(
    id="t3", page_id="pg1", type="maintenance", name="DB upgrade", title="Database upgrade",
    body="Planned upgrade.", components={"c2": "under_maintenance"}, duration_minutes=90,
)


def _json(result):
    return json.loads(result.stdout)


class TestTemplateCommands:
    def test_list_table_and_type_filter(self, cli_runner, tpls):
        tpls.v1_pages_page_id_incident_templates_get.return_value = [INCIDENT_TPL, MAINT_TPL]
        result = cli_runner.invoke(app, ["pages", "incidents", "templates", "list", "-p", "pg1", "--type", "incident"])
        assert result.exit_code == 0, result.output
        assert "API down" in result.stdout and "1h30m" in result.stdout
        tpls.v1_pages_page_id_incident_templates_get.assert_called_once_with(page_id="pg1", type="incident")

    def test_list_json(self, cli_runner, tpls):
        tpls.v1_pages_page_id_incident_templates_get.return_value = [MAINT_TPL]
        result = cli_runner.invoke(app, ["-o", "json", "pages", "incidents", "templates", "list", "-p", "pg1"])
        assert result.exit_code == 0, result.output
        assert _json(result)[0]["duration_minutes"] == 90
        tpls.v1_pages_page_id_incident_templates_get.assert_called_once_with(page_id="pg1", type=None)

    def test_list_rejects_unknown_type(self, cli_runner, tpls):
        result = cli_runner.invoke(app, ["pages", "incidents", "templates", "list", "-p", "pg1", "--type", "other"])
        assert result.exit_code == 2
        tpls.v1_pages_page_id_incident_templates_get.assert_not_called()

    def test_get_shows_message(self, cli_runner, tpls):
        tpls.v1_pages_page_id_incident_templates_template_id_get.return_value = INCIDENT_TPL
        result = cli_runner.invoke(app, ["pages", "incidents", "templates", "get", "t1", "-p", "pg1"])
        assert result.exit_code == 0, result.output
        assert "We are investigating." in result.stdout and "major_outage" in result.stdout

    def test_create_incident_template(self, cli_runner, tpls):
        tpls.v1_pages_page_id_incident_templates_post.return_value = INCIDENT_TPL
        result = cli_runner.invoke(app, ["pages", "incidents", "templates", "create", "-p", "pg1", "--type", "incident",
                                         "-n", "API down", "--title", "API is unavailable", "-b", "Investigating",
                                         "-s", "investigating", "-c", "c1=major_outage"])
        assert result.exit_code == 0, result.output
        assert tpls.v1_pages_page_id_incident_templates_post.call_args.kwargs == {
            "page_id": "pg1",
            "incident_template": {"type": "incident", "name": "API down", "title": "API is unavailable",
                                  "body": "Investigating", "status": "investigating",
                                  "components": {"c1": "major_outage"}},
        }
        assert "--template t1" in result.stdout

    def test_create_maintenance_template(self, cli_runner, tpls):
        tpls.v1_pages_page_id_incident_templates_post.return_value = MAINT_TPL
        result = cli_runner.invoke(app, ["pages", "incidents", "templates", "create", "-p", "pg1", "-t", "maintenance",
                                         "-n", "DB upgrade", "--title", "Database upgrade", "-c", "c2", "-d", "1h30m"])
        assert result.exit_code == 0, result.output
        assert tpls.v1_pages_page_id_incident_templates_post.call_args.kwargs["incident_template"] == {
            "type": "maintenance", "name": "DB upgrade", "title": "Database upgrade",
            "components": {"c2": "under_maintenance"}, "duration_minutes": 90,
        }

    @pytest.mark.parametrize("args", [
        ["--type", "maintenance", "-s", "investigating"],
        ["--type", "incident", "-d", "2h"],
        ["--type", "incident", "-c", "c1"],
        ["--type", "incident", "-c", "c1=broken"],
        ["--type", "maintenance", "-d", "soon"],
        ["--type", "maintenance", "-d", "40d"],
    ])
    def test_create_validation(self, cli_runner, tpls, args):
        result = cli_runner.invoke(app, ["pages", "incidents", "templates", "create", "-p", "pg1",
                                         "-n", "x", "--title", "x", *args])
        assert result.exit_code == 2
        tpls.v1_pages_page_id_incident_templates_post.assert_not_called()

    def test_update_sends_only_changes_and_clears(self, cli_runner, tpls):
        tpls.v1_pages_page_id_incident_templates_template_id_patch.return_value = INCIDENT_TPL
        result = cli_runner.invoke(app, ["pages", "incidents", "templates", "update", "t1", "-p", "pg1",
                                         "-n", "Renamed", "--clear-status", "--clear-components"])
        assert result.exit_code == 0, result.output
        assert tpls.v1_pages_page_id_incident_templates_template_id_patch.call_args.kwargs == {
            "page_id": "pg1", "template_id": "t1",
            "incident_template1": {"name": "Renamed", "status": None, "components": None},
        }

    def test_update_components_use_template_type(self, cli_runner, tpls):
        tpls.v1_pages_page_id_incident_templates_template_id_get.return_value = MAINT_TPL
        tpls.v1_pages_page_id_incident_templates_template_id_patch.return_value = MAINT_TPL
        result = cli_runner.invoke(app, ["pages", "incidents", "templates", "update", "t3", "-p", "pg1", "-c", "c1"])
        assert result.exit_code == 0, result.output
        assert tpls.v1_pages_page_id_incident_templates_template_id_patch.call_args.kwargs["incident_template1"] == {
            "components": {"c1": "under_maintenance"},
        }

    def test_update_requires_a_change(self, cli_runner, tpls):
        result = cli_runner.invoke(app, ["pages", "incidents", "templates", "update", "t1", "-p", "pg1"])
        assert result.exit_code == 2
        tpls.v1_pages_page_id_incident_templates_template_id_patch.assert_not_called()

    def test_delete(self, cli_runner, tpls):
        result = cli_runner.invoke(app, ["-o", "json", "pages", "incidents", "templates", "delete", "t1", "-p", "pg1", "-y"])
        assert result.exit_code == 0, result.output
        assert _json(result) == {"deleted": True, "id": "t1"}
        tpls.v1_pages_page_id_incident_templates_template_id_delete.assert_called_once_with(page_id="pg1", template_id="t1")


class TestApplyTemplates:
    def test_create_incident_from_template(self, cli_runner, tpls, incs, comps):
        tpls.v1_pages_page_id_incident_templates_template_id_get.return_value = INCIDENT_TPL
        incs.v1_pages_page_id_incidents_post.return_value = Incident(id="inc1", name="API is unavailable", status="investigating")
        result = cli_runner.invoke(app, ["pages", "incidents", "create", "-p", "pg1", "--template", "t1"])
        assert result.exit_code == 0, result.output
        assert incs.v1_pages_page_id_incidents_post.call_args.kwargs["incident_create"] == {
            "name": "API is unavailable", "status": "investigating", "deliver_notifications": True,
            "body": "We are investigating.", "components": {"c1": "major_outage"},
        }
        assert "no longer exist: gone" in result.stderr

    def test_explicit_options_override_template(self, cli_runner, tpls, incs, comps):
        tpls.v1_pages_page_id_incident_templates_template_id_get.return_value = INCIDENT_TPL
        incs.v1_pages_page_id_incidents_post.return_value = Incident(id="inc1", name="Custom", status="identified")
        result = cli_runner.invoke(app, ["pages", "incidents", "create", "-p", "pg1", "-t", "t1", "-n", "Custom",
                                         "-s", "identified", "-c", '{"c2": "partial_outage"}'])
        assert result.exit_code == 0, result.output
        payload = incs.v1_pages_page_id_incidents_post.call_args.kwargs["incident_create"]
        assert (payload["name"], payload["status"], payload["components"]) == ("Custom", "identified", {"c2": "partial_outage"})
        assert payload["body"] == "We are investigating."

    def test_create_without_template_still_requires_name_and_status(self, cli_runner, incs):
        result = cli_runner.invoke(app, ["pages", "incidents", "create", "-p", "pg1", "-s", "investigating"])
        assert result.exit_code == 2
        incs.v1_pages_page_id_incidents_post.assert_not_called()

    def test_wrong_template_type_is_rejected(self, cli_runner, tpls, incs):
        tpls.v1_pages_page_id_incident_templates_template_id_get.return_value = MAINT_TPL
        result = cli_runner.invoke(app, ["pages", "incidents", "create", "-p", "pg1", "-t", "t3"])
        assert result.exit_code == 2
        assert "maintenance template" in result.output
        incs.v1_pages_page_id_incidents_post.assert_not_called()

    def test_schedule_maintenance_from_template(self, cli_runner, tpls, sdk_apis, comps):
        tpls.v1_pages_page_id_incident_templates_template_id_get.return_value = MAINT_TPL
        incs = sdk_apis["StatusPagesIncidentsApi"]
        incs.v1_pages_page_id_incidents_post.return_value = Incident(id="m1", name="Database upgrade", status="scheduled")
        result = cli_runner.invoke(app, ["pages", "incidents", "schedule-maintenance", "-p", "pg1",
                                         "--start", "2030-01-01T02:00:00Z", "-t", "t3"])
        assert result.exit_code == 0, result.output
        payload = incs.v1_pages_page_id_incidents_post.call_args.kwargs["incident_create"]
        assert payload["name"] == "Database upgrade" and payload["body"] == "Planned upgrade."
        assert payload["scheduled_until"] == "2030-01-01T03:30:00Z"
        assert payload["components"] == {"c2": "operational"}

    def test_schedule_maintenance_end_overrides_duration(self, cli_runner, tpls, sdk_apis, comps):
        tpls.v1_pages_page_id_incident_templates_template_id_get.return_value = MAINT_TPL
        incs = sdk_apis["StatusPagesIncidentsApi"]
        incs.v1_pages_page_id_incidents_post.return_value = Incident(id="m1", name="x", status="scheduled")
        result = cli_runner.invoke(app, ["pages", "incidents", "schedule-maintenance", "-p", "pg1", "-t", "t3",
                                         "--start", "2030-01-01T02:00:00Z", "--end", "2030-01-01T06:00:00Z"])
        assert result.exit_code == 0, result.output
        assert incs.v1_pages_page_id_incidents_post.call_args.kwargs["incident_create"]["scheduled_until"] == "2030-01-01T06:00:00Z"

    def test_schedule_maintenance_needs_end_without_duration(self, cli_runner, sdk_apis):
        result = cli_runner.invoke(app, ["pages", "incidents", "schedule-maintenance", "-p", "pg1", "-n", "x",
                                         "--start", "+1d"])
        assert result.exit_code == 2
        sdk_apis["StatusPagesIncidentsApi"].v1_pages_page_id_incidents_post.assert_not_called()

    def test_update_from_template(self, cli_runner, tpls, sdk_apis, comps):
        tpls.v1_pages_page_id_incident_templates_template_id_get.return_value = RESOLVED_TPL
        incs = sdk_apis["StatusPagesIncidentsApi"]
        incs.v1_pages_page_id_incidents_incident_id_patch.return_value = Incident(id="inc1", name="API down", status="resolved")
        result = cli_runner.invoke(app, ["pages", "incidents", "updates", "add", "inc1", "-p", "pg1", "-t", "t2"])
        assert result.exit_code == 0, result.output
        assert incs.v1_pages_page_id_incidents_incident_id_patch.call_args.kwargs["incident_update_schema_edit"] == {
            "deliver_notifications": True, "status": "resolved", "body": "All good now.",
            "components": {"c1": "operational"},
        }


@pytest.mark.parametrize("value,minutes", [("90", 90), ("90m", 90), ("2h", 120), ("1h30m", 90), ("1d", 1440)])
def test_parse_duration(value, minutes):
    assert parse_duration(value) == minutes
