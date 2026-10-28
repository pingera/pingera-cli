"""
Tests for status page features: component groups, component statuses/uptime report, incident updates,
postmortems, past incidents, maintenance scheduling, page passwords, sender email domain and templates
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from pingera.exceptions import ApiException, NotFoundException
from pingera.models import (
    Component,
    Component1,
    ComponentUptime,
    EmailDomain,
    Incident,
    IncidentPostmortem,
    IncidentUpdate,
    PagePassword,
    V1PagesGetTemplatesGet200ResponseValue,
)

from pingera_cli.main import app


@pytest.fixture(autouse=True)
def wide_console():
    """Render tables wide enough that cell values aren't wrapped mid-word."""
    from pingera_cli.utils.console import console
    previous = console._width
    console.width = 200
    yield
    console._width = previous


def _json(result):
    return json.loads(result.stdout)


@pytest.fixture
def comps(sdk_apis):
    return sdk_apis["StatusPagesComponentsApi"]


@pytest.fixture
def incs(sdk_apis):
    return sdk_apis["StatusPagesIncidentsApi"]


def _components():
    return [
        Component(id="grp1", name="Databases", group=True),
        Component(id="c1", name="Postgres", group_id="grp1", status="operational"),
        Component(id="c2", name="Redis", group_id="grp1", status="major_outage"),
        Component(id="c3", name="API", status="degraded_performance"),
    ]


class TestComponentGroups:
    def test_list_shows_member_components(self, cli_runner, comps):
        comps.v1_pages_page_id_component_groups_get.return_value = [Component(id="grp1", name="Databases", group=True)]
        comps.v1_pages_page_id_components_get.return_value = _components()
        result = cli_runner.invoke(app, ["pages", "component-groups", "list", "--page-id", "pg1"])
        assert result.exit_code == 0, result.output
        assert "Databases" in result.stdout
        assert "2: Postgres, Redis" in result.stdout
        comps.v1_pages_page_id_component_groups_get.assert_called_once_with(page_id="pg1")
        comps.v1_pages_page_id_components_get.assert_called_once_with(page_id="pg1", show_groups=False)

    def test_get_json_includes_members(self, cli_runner, comps):
        comps.v1_pages_page_id_component_groups_component_id_get.return_value = Component(id="grp1", name="Databases", group=True)
        comps.v1_pages_page_id_components_get.return_value = _components()
        result = cli_runner.invoke(app, ["-o", "json", "pages", "component-groups", "get", "grp1", "-p", "pg1"])
        assert result.exit_code == 0, result.output
        data = _json(result)
        assert data["id"] == "grp1"
        assert [c["id"] for c in data["components"]] == ["c1", "c2"]

    def test_get_table_lists_members(self, cli_runner, comps):
        comps.v1_pages_page_id_component_groups_component_id_get.return_value = Component(id="grp1", name="Databases", group=True)
        comps.v1_pages_page_id_components_get.return_value = _components()
        result = cli_runner.invoke(app, ["pages", "component-groups", "get", "grp1", "-p", "pg1"])
        assert result.exit_code == 0
        assert "Redis" in result.stdout and "major_outage" in result.stdout

    def test_create_moves_components(self, cli_runner, comps):
        comps.v1_pages_page_id_component_groups_post.return_value = Component(id="grp9", name="APIs", group=True)
        result = cli_runner.invoke(app, ["pages", "component-groups", "create", "-p", "pg1", "-n", "APIs",
                                         "--position", "3", "-c", "c1", "-c", "c3"])
        assert result.exit_code == 0, result.output
        assert comps.v1_pages_page_id_component_groups_post.call_args.kwargs == {
            "page_id": "pg1", "component": {"name": "APIs", "group": True, "position": 3}
        }
        patches = [c.kwargs for c in comps.v1_pages_page_id_components_component_id_patch.call_args_list]
        assert patches == [
            {"page_id": "pg1", "component_id": "c1", "component1": {"group_id": "grp9"}},
            {"page_id": "pg1", "component_id": "c3", "component1": {"group_id": "grp9"}},
        ]
        assert "grp9" in result.stdout and "2 of 2" in result.stdout

    def test_update_keeps_group_flag(self, cli_runner, comps):
        comps.v1_pages_page_id_component_groups_component_id_patch.return_value = Component1(id="grp1", name="Stores", group=True)
        result = cli_runner.invoke(app, ["-o", "json", "pages", "component-groups", "update", "grp1", "-p", "pg1",
                                         "--name", "Stores", "--remove-component", "c2"])
        assert result.exit_code == 0, result.output
        assert comps.v1_pages_page_id_component_groups_component_id_patch.call_args.kwargs["component1"] == {"name": "Stores"}
        assert comps.v1_pages_page_id_components_component_id_patch.call_args.kwargs["component1"] == {"group_id": None}
        assert _json(result)["name"] == "Stores"

    def test_update_membership_failure_exits_1(self, cli_runner, comps):
        comps.v1_pages_page_id_components_component_id_patch.side_effect = NotFoundException(
            status=404, reason="Not Found", body='{"message": "Component not found"}')
        result = cli_runner.invoke(app, ["pages", "component-groups", "update", "grp1", "-p", "pg1", "--add-component", "nope"])
        assert result.exit_code == 1
        assert "nope: HTTP 404: Component not found" in result.stderr

    def test_update_without_changes_is_usage_error(self, cli_runner, comps):
        result = cli_runner.invoke(app, ["pages", "component-groups", "update", "grp1", "-p", "pg1"])
        assert result.exit_code == 2
        comps.v1_pages_page_id_component_groups_component_id_patch.assert_not_called()

    def test_delete_json(self, cli_runner, comps):
        result = cli_runner.invoke(app, ["-o", "json", "pages", "component-groups", "delete", "grp1", "-p", "pg1", "-y"])
        assert result.exit_code == 0
        assert _json(result) == {"deleted": True, "id": "grp1"}
        comps.v1_pages_page_id_component_groups_component_id_delete.assert_called_once_with(page_id="pg1", component_id="grp1")

    def test_delete_cancelled(self, cli_runner, comps):
        result = cli_runner.invoke(app, ["pages", "component-groups", "delete", "grp1", "-p", "pg1"], input="n\n")
        assert result.exit_code == 0
        comps.v1_pages_page_id_component_groups_component_id_delete.assert_not_called()


UPTIME = [
    {"id": "c1", "name": "Postgres", "range_start": "2026-07-30", "range_end": "2026-10-28", "uptime_percentage": 99.95,
     "major_outage": 0, "partial_outage": 3600, "warnings": [], "related_events": {"id": ["inc1"]}},
    {"id": "c3", "name": "API", "range_start": "2026-07-30", "range_end": "2026-10-28", "uptime_percentage": 97.5,
     "major_outage": 7200, "partial_outage": 0, "warnings": ["End date was adjusted to today"], "related_events": {"id": []}},
]


def _uptime():
    return [ComponentUptime.from_dict(row) for row in UPTIME]


class TestComponentExtras:
    def test_statuses(self, cli_runner, comps):
        comps.v1_component_statuses_get.return_value = ["operational", "major_outage"]
        result = cli_runner.invoke(app, ["pages", "components", "statuses"])
        assert result.exit_code == 0
        assert "major_outage" in result.stdout and "Unavailable for most" in result.stdout
        result = cli_runner.invoke(app, ["-o", "json", "pages", "components", "statuses"])
        assert _json(result) == ["operational", "major_outage"]

    def test_uptime_report_all_components_skips_groups(self, cli_runner, comps):
        comps.v1_pages_page_id_components_get.return_value = _components()
        comps.v1_pages_page_id_components_uptime_post.return_value = _uptime()
        result = cli_runner.invoke(app, ["pages", "components", "uptime-report", "-p", "pg1"])
        assert result.exit_code == 0, result.output
        comps.v1_pages_page_id_components_get.assert_called_once_with(page_id="pg1", show_groups=False)
        assert comps.v1_pages_page_id_components_uptime_post.call_args.kwargs == {
            "page_id": "pg1", "component_uptime_bulk_request": {"component_ids": ["c1", "c2", "c3"]}}
        assert "99.95%" in result.stdout and "97.50%" in result.stdout
        assert "1h" in result.stdout and "2h" in result.stdout
        assert "End date was adjusted" in result.stdout

    def test_uptime_report_include_groups(self, cli_runner, comps):
        comps.v1_pages_page_id_components_get.return_value = _components()
        comps.v1_pages_page_id_components_uptime_post.return_value = _uptime()
        result = cli_runner.invoke(app, ["pages", "components", "uptime-report", "-p", "pg1", "--include-groups"])
        assert result.exit_code == 0, result.output
        comps.v1_pages_page_id_components_get.assert_called_once_with(page_id="pg1", show_groups=True)
        assert comps.v1_pages_page_id_components_uptime_post.call_args.kwargs[
            "component_uptime_bulk_request"] == {"component_ids": ["grp1", "c1", "c2", "c3"]}

    def test_uptime_report_with_dates(self, cli_runner, comps):
        comps.v1_pages_page_id_components_uptime_post.return_value = _uptime()[:1]
        result = cli_runner.invoke(app, ["-o", "json", "pages", "components", "uptime-report", "-p", "pg1", "-c", "c1",
                                         "--from", "2026-09-01", "--to", "2026-10-01T15:00:00Z"])
        assert result.exit_code == 0, result.output
        comps.v1_pages_page_id_components_get.assert_not_called()
        assert comps.v1_pages_page_id_components_uptime_post.call_args.kwargs == {
            "page_id": "pg1", "component_uptime_bulk_request": {"component_ids": ["c1"]},
            "start": "2026-09-01", "end": "2026-10-01"}
        data = _json(result)
        assert data["start"] == "2026-09-01" and data["components"][0]["id"] == "c1"
        assert data["components"][0]["related_events"] == {"id": ["inc1"]}

    def test_uptime_report_api_error(self, cli_runner, comps):
        comps.v1_pages_page_id_components_uptime_post.side_effect = NotFoundException(
            status=404, reason="Not Found", body='{"message": "No components found."}')
        result = cli_runner.invoke(app, ["pages", "components", "uptime-report", "-p", "pg1", "-c", "x"])
        assert result.exit_code == 1
        assert "HTTP 404: No components found." in result.stderr

    def test_uptime_report_bad_date(self, cli_runner, comps):
        result = cli_runner.invoke(app, ["pages", "components", "uptime-report", "-p", "pg1", "--from", "yesterday"])
        assert result.exit_code == 2
        comps.v1_pages_page_id_components_get.assert_not_called()

    def test_single_uptime_passes_dates(self, cli_runner, comps, monkeypatch):
        from pingera_cli.commands.components import ComponentsCommand
        monkeypatch.setattr(ComponentsCommand, "get_client", lambda self: comps)
        comps.v1_pages_page_id_components_component_id_uptime_get.return_value = _uptime()[0]
        result = cli_runner.invoke(app, ["pages", "components", "uptime", "c1", "-p", "pg1", "--start", "2026-01"])
        assert result.exit_code == 0, result.output
        assert comps.v1_pages_page_id_components_component_id_uptime_get.call_args.kwargs == {
            "page_id": "pg1", "component_id": "c1", "start": "2026-01", "end": None}
        assert "99.950%" in result.stdout


UPDATES = [
    {"id": "u2", "incident_id": "inc1", "status": "in_progress", "body": "Maintenance started",
     "created_at": "2026-10-28T10:00:00Z", "deliver_notifications": True, "components": {"c1": "under_maintenance"}},
    {"id": "u1", "incident_id": "inc1", "status": "scheduled", "body": "Planned",
     "created_at": "2026-10-27T10:00:00Z", "deliver_notifications": False, "components": {}},
]


def _updates():
    return [IncidentUpdate.from_dict(u) for u in UPDATES]


class TestIncidentUpdates:
    def test_list_accepts_maintenance_statuses(self, cli_runner, incs):
        incs.v1_pages_page_id_incidents_incident_id_incident_updates_get.return_value = _updates()
        result = cli_runner.invoke(app, ["pages", "incidents", "updates", "list", "inc1", "-p", "pg1"])
        assert result.exit_code == 0, result.output
        assert "in_progress" in result.stdout and "under_maintenance" in result.stdout
        result = cli_runner.invoke(app, ["-o", "json", "pages", "incidents", "updates", "list", "inc1", "-p", "pg1"])
        assert [u["id"] for u in _json(result)] == ["u2", "u1"]
        incs.v1_pages_page_id_incidents_incident_id_incident_updates_get.assert_called_with(page_id="pg1", incident_id="inc1")

    def test_add_posts_update_via_incident_patch(self, cli_runner, incs):
        incs.v1_pages_page_id_incidents_incident_id_patch.return_value = Incident(
            id="inc1", name="API down", status="identified",
            incident_updates=[{"id": "u9", "status": "identified", "created_at": "2026-10-28T12:00:00Z"},
                              {"id": "u1", "status": "investigating", "created_at": "2026-10-28T10:00:00Z"}],
        )
        result = cli_runner.invoke(app, ["pages", "incidents", "updates", "add", "inc1", "-p", "pg1", "-s", "identified",
                                         "-b", "Found it", "-c", "c1=partial_outage", "-c", "c2:operational", "--no-notify"])
        assert result.exit_code == 0, result.output
        assert incs.v1_pages_page_id_incidents_incident_id_patch.call_args.kwargs == {
            "page_id": "pg1", "incident_id": "inc1",
            "incident_update_schema_edit": {"deliver_notifications": False, "status": "identified", "body": "Found it",
                                            "components": {"c1": "partial_outage", "c2": "operational"}},
        }
        assert "u9" in result.stdout
        incs.v1_pages_page_id_incidents_incident_id_incident_updates_post.assert_not_called()

    @pytest.mark.parametrize("args", [
        ["-s", "fixed"],
        ["-c", "c1=broken", "-s", "resolved"],
        ["-c", "c1", "-s", "resolved"],
        [],
    ])
    def test_add_validation(self, cli_runner, incs, args):
        result = cli_runner.invoke(app, ["pages", "incidents", "updates", "add", "inc1", "-p", "pg1", *args])
        assert result.exit_code == 2
        incs.v1_pages_page_id_incidents_incident_id_patch.assert_not_called()

    def test_edit(self, cli_runner, incs):
        method = incs.v1_pages_page_id_incidents_incident_id_incident_updates_incident_update_id_patch
        method.return_value = _updates()[1]
        result = cli_runner.invoke(app, ["-o", "json", "pages", "incidents", "updates", "edit", "inc1", "u1", "-p", "pg1",
                                         "-b", "Fixed", "--posted-at", "2026-10-27T09:30:00+01:00", "-c", "c1=major_outage"])
        assert result.exit_code == 0, result.output
        assert method.call_args.kwargs == {
            "page_id": "pg1", "incident_id": "inc1", "incident_update_id": "u1",
            "incident_update_edit": {"body": "Fixed", "created_at": "2026-10-27T08:30:00Z", "components": {"c1": "major_outage"}},
        }
        assert _json(result)["id"] == "u1"

    def test_edit_clear_components(self, cli_runner, incs):
        method = incs.v1_pages_page_id_incidents_incident_id_incident_updates_incident_update_id_patch
        method.return_value = _updates()[1]
        result = cli_runner.invoke(app, ["pages", "incidents", "updates", "edit", "inc1", "u1", "-p", "pg1", "--clear-components"])
        assert result.exit_code == 0, result.output
        assert method.call_args.kwargs["incident_update_edit"] == {"components": {}}

    def test_edit_rejects_future_time(self, cli_runner, incs):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        result = cli_runner.invoke(app, ["pages", "incidents", "updates", "edit", "inc1", "u1", "-p", "pg1", "--posted-at", future])
        assert result.exit_code == 2
        assert "future" in result.output

    def test_delete(self, cli_runner, incs):
        result = cli_runner.invoke(app, ["-o", "json", "pages", "incidents", "updates", "delete", "inc1", "u1", "-p", "pg1", "--confirm"])
        assert result.exit_code == 0
        assert _json(result) == {"deleted": True, "id": "u1"}
        incs.v1_pages_page_id_incidents_incident_id_incident_updates_incident_update_id_delete.assert_called_once_with(
            page_id="pg1", incident_id="inc1", incident_update_id="u1")


class TestPostmortem:
    def test_get_shows_draft(self, cli_runner, incs):
        incs.v1_pages_page_id_incidents_incident_id_postmortem_get.return_value = IncidentPostmortem(
            body_draft="## Root cause\nConnection pool exhausted", notify_subscribers=True)
        result = cli_runner.invoke(app, ["pages", "incidents", "postmortem", "get", "inc1", "-p", "pg1"])
        assert result.exit_code == 0, result.output
        assert "Draft (not published)" in result.stdout
        assert "Connection pool exhausted" in result.stdout

    def test_set_from_file(self, cli_runner, incs, tmp_path):
        md = tmp_path / "pm.md"
        md.write_text("# Postmortem\nDetails", encoding="utf-8")
        incs.v1_pages_page_id_incidents_incident_id_postmortem_put.return_value = IncidentPostmortem(body_draft="x")
        result = cli_runner.invoke(app, ["pages", "incidents", "postmortem", "set", "inc1", "-p", "pg1", "--file", str(md),
                                         "--no-notify-subscribers"])
        assert result.exit_code == 0, result.output
        assert incs.v1_pages_page_id_incidents_incident_id_postmortem_put.call_args.kwargs == {
            "page_id": "pg1", "incident_id": "inc1",
            "incident_postmortem": {"body_draft": "# Postmortem\nDetails", "notify_subscribers": False},
        }

    @pytest.mark.parametrize("args", [[], ["-b", "x", "-f", "y.md"], ["-f", "/nonexistent/pm.md"], ["-b", "  "]])
    def test_set_validation(self, cli_runner, incs, args):
        result = cli_runner.invoke(app, ["pages", "incidents", "postmortem", "set", "inc1", "-p", "pg1", *args])
        assert result.exit_code == 2
        incs.v1_pages_page_id_incidents_incident_id_postmortem_put.assert_not_called()

    def test_publish_with_notify_sets_flag_first(self, cli_runner, incs):
        incs.v1_pages_page_id_incidents_incident_id_postmortem_publish_put.return_value = IncidentPostmortem(
            body="done", published_at=datetime(2026, 10, 28, 12, tzinfo=timezone.utc))
        result = cli_runner.invoke(app, ["-o", "json", "pages", "incidents", "postmortem", "publish", "inc1", "-p", "pg1",
                                         "--notify-subscribers"])
        assert result.exit_code == 0, result.output
        assert incs.v1_pages_page_id_incidents_incident_id_postmortem_put.call_args.kwargs["incident_postmortem"] == {
            "notify_subscribers": True}
        assert _json(result)["body"] == "done"

    def test_publish_plain(self, cli_runner, incs):
        incs.v1_pages_page_id_incidents_incident_id_postmortem_publish_put.return_value = IncidentPostmortem(body="done")
        result = cli_runner.invoke(app, ["pages", "incidents", "postmortem", "publish", "inc1", "-p", "pg1"])
        assert result.exit_code == 0
        incs.v1_pages_page_id_incidents_incident_id_postmortem_put.assert_not_called()

    def test_not_found(self, cli_runner, incs):
        incs.v1_pages_page_id_incidents_incident_id_postmortem_get.side_effect = NotFoundException(
            status=404, reason="Not Found", body='{"message": "Postmortem not found"}')
        result = cli_runner.invoke(app, ["pages", "incidents", "postmortem", "get", "inc1", "-p", "pg1"])
        assert result.exit_code == 1
        assert "HTTP 404: Postmortem not found" in result.stderr


class TestIncidentExtras:
    def test_reference(self, cli_runner, incs):
        incs.v1_incident_statuses_get.return_value = ["investigating", "resolved"]
        incs.v1_maintenance_statuses_get.return_value = ["scheduled", "completed"]
        incs.v1_incident_impacts_get.return_value = ["none", "critical"]
        result = cli_runner.invoke(app, ["-o", "json", "pages", "incidents", "reference"])
        assert result.exit_code == 0
        assert _json(result) == {"incident_statuses": ["investigating", "resolved"],
                                 "maintenance_statuses": ["scheduled", "completed"], "impacts": ["none", "critical"]}
        result = cli_runner.invoke(app, ["pages", "incidents", "reference"])
        assert "Maintenance window statuses" in result.stdout and "critical" in result.stdout

    def test_log_past_simple(self, cli_runner, incs):
        incs.v1_pages_page_id_incidents_log_past_incident_post.return_value = Incident(
            id="inc7", name="API outage", status="resolved", impact="major")
        result = cli_runner.invoke(app, ["pages", "incidents", "log-past", "-p", "pg1", "-n", "API outage", "-i", "major",
                                         "--started", "2026-10-01T10:00:00Z", "--resolved", "2026-10-01T12:15:00Z",
                                         "-b", "500s everywhere", "-c", "c1=major_outage"])
        assert result.exit_code == 0, result.output
        assert incs.v1_pages_page_id_incidents_log_past_incident_post.call_args.kwargs == {
            "page_id": "pg1",
            "log_past_incident": {
                "name": "API outage", "impact": "major", "deliver_notifications": False,
                "incident_updates": [
                    {"status": "investigating", "body": "500s everywhere", "created_at": "2026-10-01T10:00:00Z",
                     "components": {"c1": "major_outage"}},
                    {"status": "resolved", "body": "This incident has been resolved.", "created_at": "2026-10-01T12:15:00Z",
                     "components": {"c1": "operational"}},
                ],
            },
        }
        assert "inc7" in result.stdout and "2h 15m" in result.stdout

    def test_log_past_updates_file(self, cli_runner, incs, tmp_path):
        path = tmp_path / "updates.json"
        path.write_text(json.dumps([
            {"status": "resolved", "body": "ok", "created_at": "2026-10-01T11:00:00Z"},
            {"status": "investigating", "body": "down", "created_at": "2026-10-01T10:00:00Z", "components": {"c1": "partial_outage"}},
        ]))
        incs.v1_pages_page_id_incidents_log_past_incident_post.return_value = Incident(id="inc8", name="x", status="resolved")
        result = cli_runner.invoke(app, ["pages", "incidents", "log-past", "-p", "pg1", "-n", "x", "-i", "minor",
                                         "--updates-file", str(path), "--notify"])
        assert result.exit_code == 0, result.output
        payload = incs.v1_pages_page_id_incidents_log_past_incident_post.call_args.kwargs["log_past_incident"]
        assert payload["deliver_notifications"] is True
        assert [u["status"] for u in payload["incident_updates"]] == ["investigating", "resolved"]
        assert payload["incident_updates"][0]["components"] == {"c1": "partial_outage"}

    @pytest.mark.parametrize("args", [
        ["-i", "huge", "--started", "3h", "--resolved", "1h", "-b", "x"],
        ["-i", "major", "--started", "3h", "-b", "x"],
        ["-i", "major", "--started", "1h", "--resolved", "3h", "-b", "x"],
        ["-i", "major", "--started", "3h", "--resolved", "+1h", "-b", "x"],
        ["-i", "major", "--updates-file", "u.json", "--started", "3h"],
    ])
    def test_log_past_validation(self, cli_runner, incs, args):
        result = cli_runner.invoke(app, ["pages", "incidents", "log-past", "-p", "pg1", "-n", "x", *args])
        assert result.exit_code == 2
        incs.v1_pages_page_id_incidents_log_past_incident_post.assert_not_called()

    def test_schedule_maintenance(self, cli_runner, incs):
        incs.v1_pages_page_id_incidents_post.return_value = Incident(id="m1", name="DB upgrade", status="scheduled")
        result = cli_runner.invoke(app, ["pages", "incidents", "schedule-maintenance", "-p", "pg1", "-n", "DB upgrade",
                                         "--start", "2030-01-01T02:00:00Z", "--end", "2030-01-01T04:00:00Z",
                                         "-c", "c1", "-b", "Upgrading", "--no-auto-complete", "--reminders", "48h, 1h"])
        assert result.exit_code == 0, result.output
        assert incs.v1_pages_page_id_incidents_post.call_args.kwargs == {
            "page_id": "pg1",
            "incident_create": {
                "name": "DB upgrade", "status": "scheduled", "impact": "maintenance",
                "scheduled_for": "2030-01-01T02:00:00Z", "scheduled_until": "2030-01-01T04:00:00Z",
                "deliver_notifications": False, "scheduled_auto_in_progress": True, "scheduled_auto_completed": False,
                "auto_transition_to_maintenance_state": True, "auto_transition_to_operational_state": True,
                "auto_transition_deliver_notifications_at_start": True,
                "auto_transition_deliver_notifications_at_end": True,
                "scheduled_remind_prior": True, "reminder_intervals": "48h,1h",
                "body": "Upgrading", "components": {"c1": "operational"},
            },
        }
        assert "m1" in result.stdout

    def test_schedule_maintenance_relative(self, cli_runner, incs):
        incs.v1_pages_page_id_incidents_post.return_value = Incident(id="m2", name="x", status="scheduled")
        result = cli_runner.invoke(app, ["-o", "json", "pages", "incidents", "schedule-maintenance", "-p", "pg1", "-n", "x",
                                         "--start", "+1d", "--end", "+26h", "--no-remind"])
        assert result.exit_code == 0, result.output
        payload = incs.v1_pages_page_id_incidents_post.call_args.kwargs["incident_create"]
        start = datetime.fromisoformat(payload["scheduled_for"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(payload["scheduled_until"].replace("Z", "+00:00"))
        assert end - start == timedelta(hours=2)
        assert "reminder_intervals" not in payload and payload["scheduled_remind_prior"] is False
        assert _json(result)["id"] == "m2"

    @pytest.mark.parametrize("args", [
        ["--start", "2h", "--end", "+3h"],
        ["--start", "2020-01-01T00:00:00Z", "--end", "+3h"],
        ["--start", "+3h", "--end", "+2h"],
        ["--start", "+3h", "--end", "+4h", "--reminders", "soon"],
    ])
    def test_schedule_maintenance_validation(self, cli_runner, incs, args):
        result = cli_runner.invoke(app, ["pages", "incidents", "schedule-maintenance", "-p", "pg1", "-n", "x", *args])
        assert result.exit_code == 2
        incs.v1_pages_page_id_incidents_post.assert_not_called()

    def test_create_help_lists_real_values(self, cli_runner):
        result = cli_runner.invoke(app, ["pages", "incidents", "create", "--help"], env={"COLUMNS": "200"})
        assert "maintenance" in result.stdout and "in_progress" in result.stdout and "under_maintenance" in result.stdout


PASSWORDS = [
    {"id": "pw1", "name": "Acme", "password_hint": "usual", "active": True, "expires_at": None,
     "created_at": "2026-10-01T10:00:00", "is_expired": False},
    {"id": "pw2", "name": None, "password_hint": None, "active": False, "expires_at": "2026-12-01T00:00:00",
     "created_at": "2026-10-02T10:00:00", "is_expired": False},
]


class TestPagePasswords:
    @pytest.fixture
    def pw_api(self, sdk_apis):
        return sdk_apis["PagePasswordsApi"]

    def test_list_without_password_field(self, cli_runner, pw_api):
        pw_api.v1_pages_page_id_passwords_get.return_value = [PagePassword.from_dict(p) for p in PASSWORDS]
        result = cli_runner.invoke(app, ["pages", "passwords", "list", "-p", "pg1"])
        assert result.exit_code == 0, result.output
        assert "Acme" in result.stdout and "usual" in result.stdout and "inactive" in result.stdout
        result = cli_runner.invoke(app, ["-o", "json", "pages", "passwords", "list", "-p", "pg1"])
        data = _json(result)
        assert [p["id"] for p in data] == ["pw1", "pw2"]
        assert data[0]["password_hint"] == "usual" and "password" not in data[0]

    def test_add(self, cli_runner, pw_api):
        pw_api.v1_pages_page_id_passwords_post.return_value = PagePassword.from_dict(PASSWORDS[0])
        result = cli_runner.invoke(app, ["pages", "passwords", "add", "-p", "pg1", "--password", "secret-123",
                                         "-n", "Acme", "--hint", "usual", "--expires", "2030-01-01"])
        assert result.exit_code == 0, result.output
        assert pw_api.v1_pages_page_id_passwords_post.call_args.kwargs == {
            "page_id": "pg1",
            "page_password_create": {"password": "secret-123", "name": "Acme", "password_hint": "usual",
                                     "expires_at": "2030-01-01T00:00:00Z"},
        }
        assert "pw1" in result.stdout
        assert "secret-123" not in result.stdout

    def test_add_prompts_for_password(self, cli_runner, pw_api):
        pw_api.v1_pages_page_id_passwords_post.return_value = PagePassword.from_dict(PASSWORDS[0])
        result = cli_runner.invoke(app, ["-o", "json", "pages", "passwords", "add", "-p", "pg1"], input="hunter2-long\nhunter2-long\n")
        assert result.exit_code == 0, result.output
        assert pw_api.v1_pages_page_id_passwords_post.call_args.kwargs[
            "page_password_create"] == {"password": "hunter2-long"}
        assert _json(result)["id"] == "pw1"

    @pytest.mark.parametrize("args", [["--password", "short"], ["--password", "long-enough", "--expires", "2020-01-01"],
                                      ["--password", "long-enough", "--hint", "x" * 201]])
    def test_add_validation(self, cli_runner, pw_api, args):
        result = cli_runner.invoke(app, ["pages", "passwords", "add", "-p", "pg1", *args])
        assert result.exit_code == 2
        pw_api.v1_pages_page_id_passwords_post.assert_not_called()

    def test_update_no_expiry(self, cli_runner, pw_api):
        pw_api.v1_pages_page_id_passwords_password_id_put.return_value = PagePassword.from_dict(PASSWORDS[0])
        result = cli_runner.invoke(app, ["pages", "passwords", "update", "pw1", "-p", "pg1", "--inactive", "--no-expiry"])
        assert result.exit_code == 0, result.output
        assert pw_api.v1_pages_page_id_passwords_password_id_put.call_args.kwargs == {
            "page_id": "pg1", "password_id": "pw1", "page_password_update": {"active": False, "expires_at": None},
        }

    def test_update_nothing(self, cli_runner, pw_api):
        result = cli_runner.invoke(app, ["pages", "passwords", "update", "pw1", "-p", "pg1"])
        assert result.exit_code == 2

    def test_delete(self, cli_runner, pw_api):
        result = cli_runner.invoke(app, ["-o", "json", "pages", "passwords", "delete", "pw1", "-p", "pg1", "-y"])
        assert result.exit_code == 0
        assert _json(result) == {"deleted": True, "id": "pw1"}


EMAIL_DOMAIN = {
    "notifications_from_email": "noreply@status.example.com",
    "notifications_from_name": "Example",
    "email_domain": "status.example.com",
    "email_domain_verified": False,
    "email_domain_status": "pending",
    "dns_records": {
        "verification": {"type": "TXT", "name": "status.example.com", "value": "unisender-validate-hash-abc"},
        "dkim": {"type": "TXT", "name": "us._domainkey.status.example.com", "value": "k=rsa; p=MIGf"},
        "spf": {"type": "TXT", "name": "status.example.com", "value": "v=spf1 include:spf.unisender.ru ~all"},
        "dmarc": {"type": "CNAME", "name": "_dmarc.status.example.com", "value": "status.example.com.dmarc.example."},
    },
}


class TestEmailDomain:
    @pytest.fixture
    def pages_api(self, sdk_apis):
        return sdk_apis["StatusPagesApi"]

    def test_show_dns_table(self, cli_runner, pages_api):
        pages_api.v1_pages_page_id_email_domain_get.return_value = EmailDomain.from_dict(EMAIL_DOMAIN)
        result = cli_runner.invoke(app, ["pages", "email-domain", "show", "-p", "pg1"])
        assert result.exit_code == 0, result.output
        for snippet in ("DNS records to create", "Domain ownership", "us._domainkey.status.example.com",
                        "v=spf1 include:spf.unisender.ru ~all", "CNAME", "pending", "email-domain verify"):
            assert snippet in result.stdout
        result = cli_runner.invoke(app, ["-o", "json", "pages", "email-domain", "show", "-p", "pg1"])
        assert _json(result) == EMAIL_DOMAIN

    def test_setup_sets_sender_first(self, cli_runner, pages_api):
        pages_api.v1_pages_page_id_email_domain_records_post.return_value = EmailDomain.from_dict(EMAIL_DOMAIN)
        result = cli_runner.invoke(app, ["pages", "email-domain", "setup", "-p", "pg1",
                                         "--from-email", "noreply@status.example.com", "--from-name", "Example"])
        assert result.exit_code == 0, result.output
        pages_api.v1_pages_page_id_patch.assert_called_once_with(
            page_id="pg1", page1={"notifications_from_email": "noreply@status.example.com", "notifications_from_name": "Example"})
        assert "Registered" in result.stdout

    def test_setup_plan_error(self, cli_runner, pages_api):
        pages_api.v1_pages_page_id_email_domain_records_post.side_effect = ApiException(
            status=402, reason="Payment Required",
            body='{"error": "email_domain", "message": "Your plan does not support sending from a custom email domain."}')
        result = cli_runner.invoke(app, ["pages", "email-domain", "setup", "-p", "pg1"])
        assert result.exit_code == 1
        assert "HTTP 402" in result.stderr and "plan does not support" in result.stderr
        pages_api.v1_pages_page_id_patch.assert_not_called()

    def test_setup_bad_email(self, cli_runner, pages_api):
        result = cli_runner.invoke(app, ["pages", "email-domain", "setup", "-p", "pg1", "--from-email", "nope"])
        assert result.exit_code == 2

    def test_verify(self, cli_runner, pages_api):
        pages_api.v1_pages_page_id_email_domain_verify_post.return_value = EmailDomain.from_dict(
            {**EMAIL_DOMAIN, "email_domain_verified": True, "email_domain_status": "confirmed"})
        result = cli_runner.invoke(app, ["pages", "email-domain", "verify", "-p", "pg1"])
        assert result.exit_code == 0
        assert "is verified" in result.stdout


TEMPLATES = {
    "Classic": V1PagesGetTemplatesGet200ResponseValue(id="tpl1", name="Classic", preview_url="https://x/classic.png"),
    "Dark": V1PagesGetTemplatesGet200ResponseValue(id="tpl2", name="Dark", preview_url=None),
}


class TestTemplates:
    @pytest.fixture
    def pages_api(self, sdk_apis, monkeypatch):
        from pingera_cli.commands.pages import PagesCommand
        api = sdk_apis["StatusPagesApi"]
        monkeypatch.setattr(PagesCommand, "get_client", lambda self: api)
        api.v1_pages_get_templates_get.return_value = TEMPLATES
        return api

    def test_list(self, cli_runner, pages_api):
        result = cli_runner.invoke(app, ["pages", "templates"])
        assert result.exit_code == 0
        assert "Classic" in result.stdout and "tpl2" in result.stdout
        result = cli_runner.invoke(app, ["-o", "json", "pages", "templates"])
        assert _json(result)["Dark"] == {"id": "tpl2", "name": "Dark"}

    @pytest.mark.parametrize("value", ["Dark", "tpl2"])
    def test_create_with_template(self, cli_runner, pages_api, value):
        from pingera.models import Page
        pages_api.v1_pages_post.return_value = Page(id="pg9", name="Status")
        result = cli_runner.invoke(app, ["pages", "create", "--name", "Status", "--template", value])
        assert result.exit_code == 0, result.output
        assert pages_api.v1_pages_post.call_args.kwargs["page"]["template_id"] == "tpl2"

    def test_update_with_template(self, cli_runner, pages_api):
        result = cli_runner.invoke(app, ["pages", "update", "pg1", "--template", "Classic"])
        assert result.exit_code == 0, result.output
        assert pages_api.v1_pages_page_id_patch.call_args.kwargs == {"page_id": "pg1", "page1": {"template_id": "tpl1"}}

    def test_unknown_template(self, cli_runner, pages_api):
        result = cli_runner.invoke(app, ["pages", "create", "--name", "Status", "--template", "Neon"])
        assert result.exit_code == 1
        assert "Unknown template 'Neon'" in result.stderr and "Classic, Dark" in result.stderr
        pages_api.v1_pages_post.assert_not_called()
