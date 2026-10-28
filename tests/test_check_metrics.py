"""
Tests for check analytics commands (uptime, status-history, response-times, stats)
"""

import json
from datetime import datetime, timezone

from pingera.models import (
    CheckUptime,
    CheckUptimeHour,
    CheckUptimeSummary,
    MonitorCheckStatusHistory,
    MonitorCheckStatusHistoryList,
)

from pingera_cli.main import app
from pingera_cli.utils.time_utils import format_duration, parse_time_arg

RESPONSE_TIMES = {
    "ru-central1": [
        {"time_bucket": "2026-10-28T10:00:00", "avg_response_time": 100.0, "p95_response_time": 180.0,
         "p99_response_time": 250.0, "sample_count": 10},
        {"time_bucket": "2026-10-28T11:00:00", "avg_response_time": 200.0, "p95_response_time": 300.0,
         "p99_response_time": 400.0, "sample_count": 30},
    ],
    "eu-west1": [
        {"time_bucket": "2026-10-28T10:00:00", "avg_response_time": 50.0, "p95_response_time": 70.0,
         "p99_response_time": 90.0, "sample_count": 5},
    ],
}

STATUS_COUNTS = {
    "ru-central1": [
        {"time_bucket": "2026-10-28T10:00:00", "total_count": 10, "ok_count": 9, "failed_count": 1,
         "degraded_count": 0, "timeout_count": 0},
        {"time_bucket": "2026-10-28T11:00:00", "total_count": 10, "ok_count": 10, "failed_count": 0,
         "degraded_count": 0, "timeout_count": 0},
    ],
    "eu-west1": [
        {"time_bucket": "2026-10-28T10:00:00", "total_count": 4, "ok_count": 2, "failed_count": 0,
         "degraded_count": 1, "timeout_count": 1},
    ],
}


def _uptime():
    return CheckUptime(
        uptime_data=[
            CheckUptimeHour(hour=datetime(2026, 10, 28, 10), status="ok", uptime=100.0),
            CheckUptimeHour(hour=datetime(2026, 10, 28, 11), status="degraded", uptime=75.5),
            CheckUptimeHour(hour=datetime(2026, 10, 28, 12), status="no_data", uptime=0),
        ],
        summary=CheckUptimeSummary(uptime=99.12, avg_response_time=245, checks=120),
    )


class TestParseTimeArg:
    def test_relative(self):
        before = datetime.now(timezone.utc)
        value = parse_time_arg("24h")
        delta = before - value
        assert 23.9 * 3600 < delta.total_seconds() < 24.1 * 3600
        assert value.tzinfo is not None

    def test_iso_naive_is_utc(self):
        assert parse_time_arg("2026-01-31") == datetime(2026, 1, 31, tzinfo=timezone.utc)

    def test_iso_with_z(self):
        assert parse_time_arg("2026-01-31T12:00:00Z") == datetime(2026, 1, 31, 12, tzinfo=timezone.utc)

    def test_invalid(self, cli_runner, sdk_apis):
        result = cli_runner.invoke(app, ["checks", "uptime", "c1", "--from", "yesterday"])
        assert result.exit_code == 2
        assert "relative time" in result.output
        sdk_apis["ChecksApi"].v1_checks_check_id_uptime_get.assert_not_called()

    def test_format_duration(self):
        assert format_duration(42) == "42s"
        assert format_duration(3 * 86400 + 4 * 3600 + 5) == "3d 4h"
        assert format_duration(125) == "2m 5s"


class TestUptime:
    def test_table(self, cli_runner, sdk_apis):
        sdk_apis["ChecksApi"].v1_checks_check_id_uptime_get.return_value = _uptime()
        result = cli_runner.invoke(app, ["checks", "uptime", "c1", "--from", "2026-10-28T00:00:00Z", "--hourly"])
        assert result.exit_code == 0, result.output
        assert "99.12%" in result.stdout
        assert "245ms" in result.stdout
        assert "120" in result.stdout
        assert "75.5%" in result.stdout
        kwargs = sdk_apis["ChecksApi"].v1_checks_check_id_uptime_get.call_args.kwargs
        assert kwargs["check_id"] == "c1"
        assert kwargs["start_time"] == datetime(2026, 10, 28, tzinfo=timezone.utc)
        assert kwargs["end_time"] is None

    def test_json(self, cli_runner, sdk_apis):
        sdk_apis["ChecksApi"].v1_checks_check_id_uptime_get.return_value = _uptime()
        result = cli_runner.invoke(app, ["-o", "json", "checks", "uptime", "c1"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["check_id"] == "c1"
        assert data["summary"]["uptime"] == 99.12
        assert len(data["uptime_data"]) == 3


class TestStatusHistory:
    def test_table(self, cli_runner, sdk_apis):
        sdk_apis["ChecksApi"].v1_checks_check_id_status_history_get.return_value = MonitorCheckStatusHistoryList(
            status_history=[
                MonitorCheckStatusHistory(status="failed", started_at=datetime(2026, 10, 28, 10, 0),
                                          ended_at=datetime(2026, 10, 28, 10, 5, 30)),
                MonitorCheckStatusHistory(status="ok", started_at=datetime(2026, 10, 28, 10, 5, 30), ended_at=None),
            ],
            pagination={"page": 1, "page_size": 20, "total_pages": 1, "total_items": 2},
        )
        result = cli_runner.invoke(app, ["checks", "status-history", "c1", "--page-size", "5"])
        assert result.exit_code == 0, result.output
        assert "5m 30s" in result.stdout
        assert "ongoing" in result.stdout
        assert "Showing 2 of 2" in result.stdout
        sdk_apis["ChecksApi"].v1_checks_check_id_status_history_get.assert_called_once_with(
            check_id="c1", page=1, page_size=5
        )

    def test_api_error(self, cli_runner, sdk_apis):
        from pingera.exceptions import NotFoundException

        sdk_apis["ChecksApi"].v1_checks_check_id_status_history_get.side_effect = NotFoundException(
            status=404, reason="NOT FOUND", body='{"message": "Monitor check not found"}'
        )
        result = cli_runner.invoke(app, ["checks", "status-history", "missing"])
        assert result.exit_code == 1
        assert "HTTP 404: Monitor check not found" in result.stderr


class TestResponseTimes:
    def test_table_aggregates_per_region(self, cli_runner, sdk_apis):
        sdk_apis["ChecksUnifiedResultsApi"].v1_checks_check_id_response_times_get.return_value = RESPONSE_TIMES
        result = cli_runner.invoke(app, ["checks", "response-times", "c1", "--buckets"])
        assert result.exit_code == 0, result.output
        # ru-central1 weighted avg: (100*10 + 200*30) / 40 = 175
        assert "175ms" in result.stdout
        assert "400ms" in result.stdout
        assert "eu-west1" in result.stdout

    def test_filters_passed(self, cli_runner, sdk_apis):
        api = sdk_apis["ChecksUnifiedResultsApi"]
        api.v1_checks_check_id_response_times_get.return_value = {}
        result = cli_runner.invoke(app, ["checks", "response-times", "c1", "--region", "ru-central1", "--status", "OK"])
        assert result.exit_code == 0
        kwargs = api.v1_checks_check_id_response_times_get.call_args.kwargs
        assert kwargs["region"] == "ru-central1"
        assert kwargs["status"] == "ok"
        assert "No results" in result.stdout

    def test_json(self, cli_runner, sdk_apis):
        sdk_apis["ChecksUnifiedResultsApi"].v1_checks_check_id_response_times_get.return_value = RESPONSE_TIMES
        result = cli_runner.invoke(app, ["-o", "json", "checks", "response-times", "c1"])
        assert json.loads(result.stdout)["regions"]["eu-west1"][0]["sample_count"] == 5


class TestStats:
    def test_all_checks(self, cli_runner, sdk_apis):
        api = sdk_apis["ChecksUnifiedResultsApi"]
        api.v1_checks_status_history_get.return_value = STATUS_COUNTS
        result = cli_runner.invoke(app, ["checks", "stats", "--from", "7d", "--without-alerts"])
        assert result.exit_code == 0, result.output
        assert "all checks" in result.stdout
        assert "95.00%" in result.stdout  # ru-central1: 19/20
        assert "All regions" in result.stdout  # 21/24
        assert "87.50%" in result.stdout
        kwargs = api.v1_checks_status_history_get.call_args.kwargs
        assert kwargs["check_id"] is None
        assert kwargs["has_alerts"] is False

    def test_invalid_result_type(self, cli_runner, sdk_apis):
        result = cli_runner.invoke(app, ["checks", "stats", "--result-type", "weird"])
        assert result.exit_code == 2

    def test_yaml(self, cli_runner, sdk_apis):
        import yaml

        sdk_apis["ChecksUnifiedResultsApi"].v1_checks_status_history_get.return_value = STATUS_COUNTS
        result = cli_runner.invoke(app, ["-o", "yaml", "checks", "stats", "c1"])
        data = yaml.safe_load(result.stdout)
        assert data["check_id"] == "c1"
        assert data["regions"]["ru-central1"][0]["ok_count"] == 9
