"""
Tests for `pngr alerts` (fired alerts), `pngr alerts rules` and `pngr alerts channels`
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from pingera.models import (
    Alert,
    AlertChannel,
    AlertChannelTestDelivery,
    AlertChannelTestResult,
    AlertList,
    AlertStats,
)

from pingera_cli.commands.alert_common import channel_target, mask_config, mask_url, parse_seconds
from pingera_cli.main import app


def raw(data, status=200):
    """Fake urllib3 response returned by the SDK *_without_preload_content methods."""
    return Mock(status=status, reason="OK" if status < 400 else "ERR",
                data=json.dumps(data).encode() if data is not None else b"")


def alert(alert_id="al1", status="firing", fired_at=None, **kw):
    return Alert(id=alert_id, status=status, severity=kw.pop("severity", "high"), title=kw.pop("title", "API down"),
                 check_id="chk1", check_name="API", rule_id="r1", rule_name="API rule",
                 fired_at=fired_at or datetime(2026, 10, 28, 10, 0), duration=3720, **kw)


# Real backend shape: `channels` objects, no `channel_ids`
RULE = {
    "id": "r1", "name": "API flapping", "check_id": "chk1", "check_name": "API health", "enabled": False,
    "severity": "high", "condition": "consecutive_failures", "condition_parameters": {"count": 3},
    "cooldown_period": 600, "auto_resolve": False, "multi_region_mode": "majority", "multi_region_threshold": None,
    "created_at": "2026-10-01T10:00:00", "updated_at": "2026-10-02T10:00:00",
    "channels": [
        {"id": "ch1", "name": "Ops mail", "type": "email", "enabled": True,
         "configuration": {"recipients": ["ops@example.com"]}},
        {"id": "ch2", "name": "Slack", "type": "webhook", "enabled": True,
         "configuration": {"url": "https://hooks.slack.com/services/T00/B00/SECRETPATH",
                           "headers": {"Authorization": "Bearer topsecret"}}},
    ],
}

WEBHOOK = AlertChannel(id="ch2", name="Slack", type="webhook", enabled=False,
                       configuration={"url": "https://hooks.slack.com/services/T00/B00/SECRETPATH?token=abc",
                                      "method": "POST", "headers": {"Authorization": "Bearer topsecret",
                                                                    "Content-Type": "application/json"},
                                      "bot_token": "123:ABC"})


@pytest.fixture
def api(sdk_apis):
    return sdk_apis["AlertsApi"]


@pytest.fixture(autouse=True)
def wide_console(monkeypatch):
    """Avoid table cell wrapping so assertions can match whole values."""
    from pingera_cli.utils.console import console, error_console

    for c in (console, error_console):
        monkeypatch.setattr(c, "_width", 250)


class TestHelpers:
    def test_mask_url(self):
        assert mask_url("https://hooks.slack.com/services/T/B/X") == "https://hooks.slack.com/***"
        assert mask_url("https://example.com") == "https://example.com/"
        assert mask_url("https://example.com:8443/?k=v") == "https://example.com:8443/***"
        assert mask_url("not a url") == "********"

    def test_mask_config(self):
        masked = mask_config(WEBHOOK.configuration)
        assert masked["headers"] == {"Authorization": "********", "Content-Type": "application/json"}
        assert masked["bot_token"] == "********"
        assert "SECRETPATH" not in masked["url"] and "abc" not in masked["url"]
        assert WEBHOOK.configuration["bot_token"] == "123:ABC"  # original untouched

    def test_channel_target(self):
        assert channel_target("email", {"recipients": ["a@x", "b@x", "c@x", "d@x"]}) == "a@x, b@x, c@x (+1)"
        assert channel_target("telegram", {"chat_id": "42"}) == "chat 42"
        assert channel_target("webhook", {"url": "https://h.io/p", "method": "put"}) == "PUT https://h.io/***"

    def test_parse_seconds(self):
        assert parse_seconds("300", "--x") == 300
        assert parse_seconds("10m", "--x") == 600
        assert parse_seconds("1d", "--x") == 86400


class TestAlerts:
    def test_list_table_and_filters(self, cli_runner, api):
        api.v1_alerts_get.return_value = AlertList(
            alerts=[alert(), alert("al2", status="resolved", severity="low", title="Slow")],
            pagination={"page": 1, "pages": 3, "per_page": 2, "total": 6, "has_next": True, "has_prev": False},
        )
        result = cli_runner.invoke(app, ["alerts", "list", "--status", "active", "--check", "chk1",
                                         "--severity", "high", "--per-page", "2"])
        assert result.exit_code == 0, result.output
        assert "al1" in result.stdout and "Slow" in result.stdout
        assert "1h 2m" in result.stdout
        assert "Showing 2 of 6" in result.stdout and "--page 2" in result.stdout
        api.v1_alerts_get.assert_called_once_with(status="active", check_id="chk1", severity="high", page=1, per_page=2)

    def test_list_invalid_status(self, cli_runner, api):
        result = cli_runner.invoke(app, ["alerts", "list", "--status", "open"])
        assert result.exit_code == 2
        api.v1_alerts_get.assert_not_called()

    def test_list_date_range_scans_pages(self, cli_runner, api):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        page1 = AlertList(alerts=[alert("new", fired_at=now - timedelta(minutes=10)),
                                  alert("in1", fired_at=now - timedelta(hours=5))],
                          pagination={"page": 1, "pages": 2, "total": 4, "has_next": True})
        page2 = AlertList(alerts=[alert("in2", fired_at=now - timedelta(hours=20)),
                                  alert("old", fired_at=now - timedelta(days=3))],
                          pagination={"page": 2, "pages": 2, "total": 4, "has_next": False})
        api.v1_alerts_get.side_effect = [page1, page2]
        result = cli_runner.invoke(app, ["-o", "json", "alerts", "list", "--from", "24h", "--to", "1h"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert [a["id"] for a in data["alerts"]] == ["in1", "in2"]
        assert data["date_filter"]["scanned"] == 4
        assert data["date_filter"]["truncated"] is False
        assert api.v1_alerts_get.call_count == 2
        assert api.v1_alerts_get.call_args.kwargs["page"] == 2
        assert api.v1_alerts_get.call_args.kwargs["per_page"] == 100

    def test_list_date_range_rejects_page(self, cli_runner, api):
        result = cli_runner.invoke(app, ["alerts", "list", "--from", "7d", "--page", "2"])
        assert result.exit_code == 2

    def test_get(self, cli_runner, api):
        api.v1_alerts_alert_id_get.return_value = alert(
            description="Failed 3 times", alert_metadata={"consecutive_failures": 3},
            trigger_results=[{"result_id": "res1", "is_primary": True, "status": "failed", "region": "ru-central1",
                              "error_message": "Connection timeout", "created_at": "2026-10-28T10:00:00"}],
            regional_summary={"total_regions": 3, "failed_regions": 2, "regions": ["ru-central1", "eu-west1"]},
        )
        result = cli_runner.invoke(app, ["alerts", "get", "al1"])
        assert result.exit_code == 0, result.output
        for expected in ("API rule", "Failed 3 times", "consecutive_failures=3", "2 of 3 failed", "Connection timeout"):
            assert expected in result.stdout

    def test_ack_and_resolve(self, cli_runner, api):
        api.v1_alerts_alert_id_acknowledge_post.return_value = alert(status="acknowledged")
        result = cli_runner.invoke(app, ["alerts", "ack", "al1"])
        assert result.exit_code == 0
        assert "acknowledged" in result.stdout
        api.v1_alerts_alert_id_acknowledge_post.assert_called_once_with(alert_id="al1")

        api.v1_alerts_alert_id_resolve_post.return_value = alert(status="resolved")
        result = cli_runner.invoke(app, ["-o", "json", "alerts", "resolve", "al1"])
        assert json.loads(result.stdout)["status"] == "resolved"

    def test_ack_error(self, cli_runner, api):
        from pingera.exceptions import BadRequestException

        api.v1_alerts_alert_id_acknowledge_post.side_effect = BadRequestException(
            status=400, reason="BAD REQUEST", body='{"message": "Only \\"firing\\" alerts can be acknowledged."}')
        result = cli_runner.invoke(app, ["alerts", "ack", "al1"])
        assert result.exit_code == 1
        assert "HTTP 400" in result.stderr and "can be acknowledged" in result.stderr

    def test_notifications_tolerates_backend_values(self, cli_runner, api):
        # Values outside the SDK enums (max, 'alert', 'cancelled') come from the real backend
        api.v1_alerts_alert_id_notifications_get_without_preload_content.return_value = raw([
            {"id": "n1", "channel_name": "Ops", "channel_type": "max", "notification_type": "alert",
             "status": "cancelled", "retry_count": 0, "created_at": "2026-10-28T10:00:00", "sent_at": None},
            {"id": "n2", "channel_name": "Ops", "channel_type": "email", "notification_type": "resolution",
             "status": "failed", "retry_count": 2, "error_message": "SMTP timeout",
             "created_at": "2026-10-28T11:00:00"},
        ])
        result = cli_runner.invoke(app, ["alerts", "notifications", "al1"])
        assert result.exit_code == 0, result.output
        assert "cancelled" in result.stdout and "SMTP timeout" in result.stdout
        assert "2 notification(s), 1 failed" in result.stdout

        result = cli_runner.invoke(app, ["-o", "json", "alerts", "notifications", "al1"])
        assert json.loads(result.stdout)[0]["channel_type"] == "max"

    def test_notifications_404(self, cli_runner, api):
        api.v1_alerts_alert_id_notifications_get_without_preload_content.return_value = raw(
            {"error": "Alert not found"}, status=404)
        result = cli_runner.invoke(app, ["alerts", "notifications", "nope"])
        assert result.exit_code == 1
        assert "HTTP 404: Alert not found" in result.stderr

    def test_stats(self, cli_runner, api):
        api.v1_alerts_stats_get.return_value = AlertStats(
            active_alerts=2, recent_alerts=23, total_rules=5, total_channels=3,
            severity_breakdown={"critical": 3, "low": 2})
        result = cli_runner.invoke(app, ["alerts", "stats"])
        assert result.exit_code == 0
        assert "23" in result.stdout and "critical" in result.stdout
        result = cli_runner.invoke(app, ["-o", "yaml", "alerts", "stats"])
        import yaml
        assert yaml.safe_load(result.stdout)["total_rules"] == 5


class TestRules:
    def test_list(self, cli_runner, api):
        other = {**RULE, "id": "r2", "check_id": "chk2", "enabled": True, "channels": []}
        api.v1_alerts_rules_get_without_preload_content.return_value = raw([RULE, other])
        result = cli_runner.invoke(app, ["alerts", "rules", "list", "--check", "chk1"])
        assert result.exit_code == 0, result.output
        assert "3 consecutive failures" in result.stdout
        assert "Ops mail, Slack" in result.stdout
        assert "10m" in result.stdout
        assert "r2" not in result.stdout

        result = cli_runner.invoke(app, ["-o", "json", "alerts", "rules", "list", "--enabled"])
        assert [r["id"] for r in json.loads(result.stdout)] == ["r2"]

    def test_get_renders_readably_and_masks(self, cli_runner, api):
        api.v1_alerts_rules_rule_id_get_without_preload_content.return_value = raw(RULE)
        result = cli_runner.invoke(app, ["alerts", "rules", "get", "r1"])
        assert result.exit_code == 0, result.output
        for expected in ("API health", "3 consecutive failures", "majority of regions fail", "10m between alerts",
                         "paused", "ops@example.com", "https://hooks.slack.com/***"):
            assert expected in result.stdout
        assert "SECRETPATH" not in result.stdout and "topsecret" not in result.stdout

    def test_create_with_flags(self, cli_runner, api):
        api.v1_alerts_rules_post_without_preload_content.return_value = raw({**RULE, "id": "rnew"}, status=201)
        result = cli_runner.invoke(app, [
            "alerts", "rules", "create", "-n", "API flapping", "-c", "chk1", "--count", "3",
            "--channel", "ch1", "--channel", "ch2", "--channel", "ch1", "--severity", "high", "--cooldown", "10m",
            "--no-auto-resolve", "--regions-count", "2"])
        assert result.exit_code == 0, result.output
        assert "rnew" in result.stdout
        body = api.v1_alerts_rules_post_without_preload_content.call_args.kwargs["alert_rule"]
        assert body == {
            "name": "API flapping", "check_id": "chk1", "condition": "consecutive_failures",
            "condition_parameters": {"count": 3}, "channel_ids": ["ch1", "ch2"], "severity": "high",
            "cooldown_period": 600, "auto_resolve": False, "multi_region_mode": "specific_count",
            "multi_region_threshold": {"count": 2},
        }

    def test_create_uptime_defaults_condition(self, cli_runner, api):
        api.v1_alerts_rules_post_without_preload_content.return_value = raw(RULE, status=201)
        result = cli_runner.invoke(app, ["alerts", "rules", "create", "-n", "Up", "-c", "chk1", "--threshold", "99.5",
                                         "--window", "1d", "--channel", "ch1"])
        assert result.exit_code == 0, result.output
        body = api.v1_alerts_rules_post_without_preload_content.call_args.kwargs["alert_rule"]
        assert body["condition"] == "uptime_below_threshold"
        assert body["condition_parameters"] == {"threshold": 99.5, "time_window": 86400}

        cli_runner.invoke(app, ["alerts", "rules", "create", "-n", "Down", "-c", "chk1", "--channel", "ch1"])
        body = api.v1_alerts_rules_post_without_preload_content.call_args.kwargs["alert_rule"]
        assert body["condition"] == "check_failed"

    def test_create_from_file_with_overrides(self, cli_runner, api, tmp_path):
        path = tmp_path / "rule.yaml"
        path.write_text("name: From file\ncheck_id: chk9\ncondition: consecutive_failures\n"
                        "condition_parameters: {count: 2}\nchannels: [{id: chA}, {id: chB}]\nid: ignored\n")
        api.v1_alerts_rules_post_without_preload_content.return_value = raw(RULE, status=201)
        result = cli_runner.invoke(app, ["alerts", "rules", "create", "-f", str(path), "--count", "4",
                                         "--name", "Override"])
        assert result.exit_code == 0, result.output
        body = api.v1_alerts_rules_post_without_preload_content.call_args.kwargs["alert_rule"]
        assert body["name"] == "Override"
        assert body["check_id"] == "chk9"
        assert body["channel_ids"] == ["chA", "chB"]
        assert body["condition_parameters"] == {"count": 4}
        assert "id" not in body

    @pytest.mark.parametrize("args, message", [
        (["-n", "x", "-c", "c"], "--channel"),
        (["-n", "x", "-c", "c", "--channel", "ch", "--condition", "uptime_below_threshold"], "--threshold"),
        (["-n", "x", "-c", "c", "--channel", "ch", "--threshold", "100"], "between 0 and 100"),
        (["-n", "x", "-c", "c", "--channel", "ch", "--count", "2", "--threshold", "50"], "mutually exclusive"),
        (["-n", "x", "-c", "c", "--channel", "ch", "--condition", "check_failed", "--count", "2"], "--count"),
        (["-n", "x", "-c", "c", "--channel", "ch", "--regions", "specific_count"], "--regions-count"),
        (["-n", "x", "-c", "c", "--channel", "ch", "--severity", "urgent"], "urgent"),
        (["-n", "x", "-c", "c", "--channel", "ch", "--cooldown", "soon"], "duration"),
    ])
    def test_create_validation(self, cli_runner, api, args, message):
        result = cli_runner.invoke(app, ["alerts", "rules", "create", *args])
        assert result.exit_code == 2
        assert message in result.output
        api.v1_alerts_rules_post_without_preload_content.assert_not_called()

    def test_create_file_unknown_field(self, cli_runner, api, tmp_path):
        path = tmp_path / "rule.json"
        path.write_text(json.dumps({"name": "x", "check": "chk1"}))
        result = cli_runner.invoke(app, ["alerts", "rules", "create", "-f", str(path)])
        assert result.exit_code == 2
        assert "check" in result.output

    def test_update_sends_full_rule_with_changes(self, cli_runner, api):
        api.v1_alerts_rules_rule_id_get_without_preload_content.return_value = raw(RULE)
        api.v1_alerts_rules_rule_id_put_without_preload_content.return_value = raw(RULE)
        result = cli_runner.invoke(app, ["alerts", "rules", "update", "r1", "--name", "Renamed", "--count", "5"])
        assert result.exit_code == 0, result.output
        kwargs = api.v1_alerts_rules_rule_id_put_without_preload_content.call_args.kwargs
        assert kwargs["rule_id"] == "r1"
        # unchanged fields are preserved (the SDK model would otherwise reset enabled/cooldown/auto_resolve)
        assert kwargs["alert_rule1"] == {
            "name": "Renamed", "enabled": False, "severity": "high", "condition": "consecutive_failures",
            "condition_parameters": {"count": 5}, "cooldown_period": 600, "auto_resolve": False,
            "multi_region_mode": "majority", "channel_ids": ["ch1", "ch2"],
        }

    def test_update_condition_change_resets_params(self, cli_runner, api):
        api.v1_alerts_rules_rule_id_get_without_preload_content.return_value = raw(RULE)
        api.v1_alerts_rules_rule_id_put_without_preload_content.return_value = raw(RULE)
        result = cli_runner.invoke(app, ["alerts", "rules", "update", "r1", "--threshold", "99", "--channel", "ch3"])
        assert result.exit_code == 0, result.output
        body = api.v1_alerts_rules_rule_id_put_without_preload_content.call_args.kwargs["alert_rule1"]
        assert body["condition"] == "uptime_below_threshold"
        assert body["condition_parameters"] == {"threshold": 99}
        assert body["channel_ids"] == ["ch3"]

    def test_update_ignores_check_change(self, cli_runner, api, tmp_path):
        path = tmp_path / "rule.json"
        path.write_text(json.dumps({"check_id": "other", "severity": "low"}))
        api.v1_alerts_rules_rule_id_get_without_preload_content.return_value = raw(RULE)
        api.v1_alerts_rules_rule_id_put_without_preload_content.return_value = raw(RULE)
        result = cli_runner.invoke(app, ["alerts", "rules", "update", "r1", "-f", str(path)])
        assert result.exit_code == 0, result.output
        assert "can't be changed" in result.stdout
        body = api.v1_alerts_rules_rule_id_put_without_preload_content.call_args.kwargs["alert_rule1"]
        assert "check_id" not in body and body["severity"] == "low"

    def test_update_nothing(self, cli_runner, api):
        result = cli_runner.invoke(app, ["alerts", "rules", "update", "r1"])
        assert result.exit_code == 2
        api.v1_alerts_rules_rule_id_get_without_preload_content.assert_not_called()

    def test_enable_disable(self, cli_runner, api):
        api.v1_alerts_rules_rule_id_get_without_preload_content.return_value = raw(RULE)
        api.v1_alerts_rules_rule_id_put_without_preload_content.return_value = raw({**RULE, "enabled": True})
        result = cli_runner.invoke(app, ["-o", "json", "alerts", "rules", "enable", "r1"])
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["enabled"] is True
        body = api.v1_alerts_rules_rule_id_put_without_preload_content.call_args.kwargs["alert_rule1"]
        assert body["enabled"] is True and body["cooldown_period"] == 600

        result = cli_runner.invoke(app, ["alerts", "rules", "disable", "r1"])
        assert result.exit_code == 0
        body = api.v1_alerts_rules_rule_id_put_without_preload_content.call_args.kwargs["alert_rule1"]
        assert body["enabled"] is False

    def test_get_404(self, cli_runner, api):
        api.v1_alerts_rules_rule_id_get_without_preload_content.return_value = raw(
            {"message": "Alert rule not found"}, status=404)
        result = cli_runner.invoke(app, ["alerts", "rules", "disable", "nope"])
        assert result.exit_code == 1
        assert "HTTP 404: Alert rule not found" in result.stderr
        api.v1_alerts_rules_rule_id_put_without_preload_content.assert_not_called()

    def test_delete(self, cli_runner, api):
        result = cli_runner.invoke(app, ["alerts", "rules", "delete", "r1"], input="n\n")
        assert result.exit_code == 0
        api.v1_alerts_rules_rule_id_delete.assert_not_called()

        result = cli_runner.invoke(app, ["-o", "json", "alerts", "rules", "delete", "r1", "-y"])
        assert result.exit_code == 0
        assert json.loads(result.stdout) == {"deleted": True, "id": "r1"}
        api.v1_alerts_rules_rule_id_delete.assert_called_once_with(rule_id="r1")


class TestChannels:
    def test_list_masks_secrets(self, cli_runner, api):
        api.v1_alerts_channels_get.return_value = [
            WEBHOOK,
            AlertChannel(id="ch1", name="Ops", type="email", configuration={"recipients": ["ops@example.com"]}),
        ]
        result = cli_runner.invoke(app, ["alerts", "channels", "list"])
        assert result.exit_code == 0, result.output
        assert "POST https://hooks.slack.com/***" in result.stdout
        assert "ops@example.com" in result.stdout
        assert "SECRETPATH" not in result.stdout and "topsecret" not in result.stdout

        result = cli_runner.invoke(app, ["-o", "json", "alerts", "channels", "list", "--type", "email"])
        assert [c["id"] for c in json.loads(result.stdout)] == ["ch1"]

    def test_get_masks_secrets(self, cli_runner, api):
        api.v1_alerts_channels_channel_id_get.return_value = WEBHOOK
        result = cli_runner.invoke(app, ["alerts", "channels", "get", "ch2"])
        assert result.exit_code == 0, result.output
        assert "Authorization=********" in result.stdout
        assert "Content-Type=application/json" in result.stdout
        for secret in ("SECRETPATH", "topsecret", "123:ABC", "token=abc"):
            assert secret not in result.stdout

        result = cli_runner.invoke(app, ["-o", "json", "alerts", "channels", "get", "ch2"])
        assert json.loads(result.stdout)["configuration"]["bot_token"] == "123:ABC"

    @pytest.mark.parametrize("args, expected", [
        (["--email", "a@example.com", "--email", "b@example.com"],
         {"type": "email", "configuration": {"recipients": ["a@example.com", "b@example.com"]}}),
        (["--url", "https://example.com/h", "--method", "put", "-H", "Authorization: Bearer x", "--timeout", "10"],
         {"type": "webhook", "configuration": {"url": "https://example.com/h", "method": "PUT",
                                               "headers": {"Authorization": "Bearer x"}, "timeout": 10}}),
        (["--type", "telegram", "--chat-id", "42"], {"type": "telegram", "configuration": {"chat_id": "42"}}),
        (["--type", "max", "--chat-id", "42"], {"type": "max", "configuration": {"chat_id": "42"}}),
        (["--phone", "+79998887766"], {"type": "sms", "configuration": {"phone_numbers": ["+79998887766"]}}),
        (["--page-id", "pg", "--component-id", "cmp"],
         {"type": "statuspage", "configuration": {"page_id": "pg", "component_id": "cmp"}}),
    ])
    def test_create_per_type(self, cli_runner, api, args, expected):
        api.v1_alerts_channels_post.return_value = AlertChannel(id="new", name="N", type=expected["type"],
                                                                configuration=expected["configuration"])
        result = cli_runner.invoke(app, ["alerts", "channels", "create", "-n", "N", *args])
        assert result.exit_code == 0, result.output
        assert "new" in result.stdout
        api.v1_alerts_channels_post.assert_called_once_with(alert_channel={"name": "N", **expected})

    @pytest.mark.parametrize("args, message", [
        (["--chat-id", "42"], "--type"),
        (["--type", "email", "--url", "https://x.io"], "only valid for webhook"),
        (["--phone", "89998887766"], "E.164"),
        (["--type", "webhook", "--url", "ftp://x"], "http(s)"),
        (["--type", "email"], "at least one recipient"),
        (["--type", "pager", "--config", "{}"], "pager"),
        (["--url", "https://x.io", "--method", "DELETE"], "POST, PUT, PATCH"),
        (["--url", "https://x.io", "-H", "no-colon"], "Name: value"),
        (["--url", "https://x.io", "--config", "[1]"], "JSON object"),
        (["--type", "sms", "--phone", "+79998887766", "--test"], "supported for"),
    ])
    def test_create_validation(self, cli_runner, api, args, message):
        result = cli_runner.invoke(app, ["alerts", "channels", "create", "-n", "N", *args])
        assert result.exit_code == 2
        assert message in result.output
        api.v1_alerts_channels_post.assert_not_called()

    def test_create_from_file_with_config_override(self, cli_runner, api, tmp_path):
        path = tmp_path / "ch.json"
        path.write_text(json.dumps({"name": "File", "type": "webhook", "id": "ignored",
                                    "configuration": {"url": "https://example.com/a", "timeout": 30, "x": 1}}))
        api.v1_alerts_channels_post.return_value = WEBHOOK
        result = cli_runner.invoke(app, ["alerts", "channels", "create", "-f", str(path), "--disabled",
                                         "--config", '{"timeout": 5, "x": null}', "--url", "https://example.com/b"])
        assert result.exit_code == 0, result.output
        api.v1_alerts_channels_post.assert_called_once_with(alert_channel={
            "name": "File", "type": "webhook", "enabled": False,
            "configuration": {"url": "https://example.com/b", "timeout": 5}})

    def test_create_with_test_first(self, cli_runner, api):
        api.v1_alerts_channels_test_post.return_value = AlertChannelTestResult(success=True, results=[])
        api.v1_alerts_channels_post.return_value = WEBHOOK
        result = cli_runner.invoke(app, ["alerts", "channels", "create", "-n", "H", "--url", "https://e.io/h", "--test"])
        assert result.exit_code == 0, result.output
        api.v1_alerts_channels_test_post.assert_called_once_with(alert_channel_test_request={
            "name": "H", "type": "webhook", "configuration": {"url": "https://e.io/h"}})
        api.v1_alerts_channels_post.assert_called_once()

    def test_create_with_failed_test_aborts(self, cli_runner, api):
        api.v1_alerts_channels_test_post.return_value = AlertChannelTestResult(success=False, error="HTTP 500")
        result = cli_runner.invoke(app, ["-o", "json", "alerts", "channels", "create", "-n", "H",
                                         "--url", "https://e.io/h", "--test"])
        assert result.exit_code == 1
        assert result.stdout == ""
        assert "not created" in result.stderr
        api.v1_alerts_channels_post.assert_not_called()

    def test_update_merges_into_current(self, cli_runner, api):
        api.v1_alerts_channels_channel_id_get.return_value = WEBHOOK
        api.v1_alerts_channels_channel_id_put.return_value = WEBHOOK
        result = cli_runner.invoke(app, ["alerts", "channels", "update", "ch2", "--name", "Renamed",
                                         "-H", "Authorization:", "-H", "X-New: 1", "--config", '{"bot_token": null}'])
        assert result.exit_code == 0, result.output
        kwargs = api.v1_alerts_channels_channel_id_put.call_args.kwargs
        assert kwargs["channel_id"] == "ch2"
        assert kwargs["alert_channel1"] == {
            "name": "Renamed", "type": "webhook", "enabled": False,  # disabled state preserved
            "configuration": {"url": WEBHOOK.configuration["url"], "method": "POST",
                              "headers": {"Content-Type": "application/json", "X-New": "1"}},
        }
        assert "topsecret" not in result.stdout

    def test_update_rejects_other_type_flags(self, cli_runner, api):
        api.v1_alerts_channels_channel_id_get.return_value = WEBHOOK
        result = cli_runner.invoke(app, ["alerts", "channels", "update", "ch2", "--email", "a@example.com"])
        assert result.exit_code == 2
        assert "only valid for email" in result.output
        api.v1_alerts_channels_channel_id_put.assert_not_called()

    def test_update_nothing(self, cli_runner, api):
        result = cli_runner.invoke(app, ["alerts", "channels", "update", "ch2"])
        assert result.exit_code == 2

    def test_delete_in_use(self, cli_runner, api):
        from pingera.exceptions import BadRequestException

        api.v1_alerts_channels_channel_id_delete.side_effect = BadRequestException(
            status=400, reason="BAD", body='{"error": "Cannot delete channel that is used by alert rules"}')
        result = cli_runner.invoke(app, ["alerts", "channels", "delete", "ch1", "--confirm"])
        assert result.exit_code == 1
        assert "used by alert rules" in result.stderr

    def test_test_saved_channel(self, cli_runner, api):
        api.v1_alerts_channels_channel_id_test_post.return_value = AlertChannelTestResult(
            success=True, results=[AlertChannelTestDelivery(recipient="https://hooks.slack.com/services/SECRET",
                                                            success=True)])
        result = cli_runner.invoke(app, ["alerts", "channels", "test", "ch2"])
        assert result.exit_code == 0, result.output
        assert "Test passed" in result.stdout
        assert "SECRET" not in result.stdout
        api.v1_alerts_channels_channel_id_test_post.assert_called_once_with(channel_id="ch2")

    def test_test_unsaved_failure_exit_code(self, cli_runner, api):
        api.v1_alerts_channels_test_post.return_value = AlertChannelTestResult(
            success=False, error="Chat not found",
            results=[AlertChannelTestDelivery(recipient="42", success=False, error="Chat not found")])
        result = cli_runner.invoke(app, ["-o", "json", "alerts", "channels", "test", "--type", "telegram",
                                         "--chat-id", "42", "--name", "TG"])
        assert result.exit_code == 1
        assert json.loads(result.stdout)["error"] == "Chat not found"
        api.v1_alerts_channels_test_post.assert_called_once_with(alert_channel_test_request={
            "type": "telegram", "configuration": {"chat_id": "42"}, "name": "TG"})

    @pytest.mark.parametrize("args, message", [
        ([], "CHANNEL_ID"),
        (["ch1", "--url", "https://x.io"], "not both"),
        (["--type", "statuspage", "--config", '{"page_id": "p"}'], "supported for"),
    ])
    def test_test_usage_errors(self, cli_runner, api, args, message):
        result = cli_runner.invoke(app, ["alerts", "channels", "test", *args])
        assert result.exit_code == 2
        assert message in result.output
