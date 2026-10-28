"""
Shared helpers for status page commands (enums, parsing, raw API calls)
"""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode

import typer

from .base import to_plain
from ..utils.time_utils import parse_time_arg

# Values mirror the backend enums (models.ComponentStatus / IncidentStatus / IncidentImpact)
COMPONENT_STATUSES = ("operational", "degraded_performance", "partial_outage", "major_outage", "under_maintenance")
INCIDENT_STATUSES = ("investigating", "identified", "monitoring", "resolved")
MAINTENANCE_STATUSES = ("scheduled", "in_progress", "verifying", "completed")
INCIDENT_IMPACTS = ("none", "minor", "major", "critical", "maintenance")

DESCRIPTIONS = {
    "operational": "Working normally",
    "degraded_performance": "Slow or partially degraded",
    "partial_outage": "Unavailable for some users",
    "major_outage": "Unavailable for most or all users",
    "under_maintenance": "Planned maintenance in progress",
    "investigating": "Problem reported, looking into it",
    "identified": "Cause found, fix in progress",
    "monitoring": "Fix deployed, watching results",
    "resolved": "Incident is over",
    "scheduled": "Maintenance planned for the future",
    "in_progress": "Maintenance is underway",
    "verifying": "Maintenance done, verifying",
    "completed": "Maintenance is over",
    "none": "No user impact",
    "minor": "Minor impact (counts as partial outage in uptime)",
    "major": "Major impact (counts as major outage in uptime)",
    "critical": "Critical impact (counts as major outage in uptime)",
    "maintenance": "Planned maintenance (for maintenance windows)",
}

_STYLE = {
    "operational": "green",
    "degraded_performance": "yellow",
    "partial_outage": "dark_orange",
    "major_outage": "red",
    "under_maintenance": "blue",
    "investigating": "red",
    "identified": "dark_orange",
    "monitoring": "yellow",
    "resolved": "green",
    "scheduled": "blue",
    "in_progress": "blue",
    "verifying": "yellow",
    "completed": "green",
    "none": "dim",
    "minor": "yellow",
    "major": "dark_orange",
    "critical": "red",
    "maintenance": "blue",
}

COMPONENT_SPEC_HELP = f"Component status change as ID=STATUS (repeatable). STATUS: {', '.join(COMPONENT_STATUSES)}"

_FUTURE_RELATIVE = re.compile(r"^\+\s*(\d+)\s*([mhdw])$")
_UNITS = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}


def styled(value: Any) -> str:
    """Colorize a known status/impact value for rich output."""
    if value is None or value == "":
        return "-"
    text = str(value)
    style = _STYLE.get(text)
    return f"[{style}]{text}[/{style}]" if style else text


def text(value: Any, default: str = "-") -> str:
    """Safe display string for possibly missing / non-string API values."""
    if value is None or value == "":
        return default
    return str(value)


def truncate(value: Any, length: int = 60) -> str:
    value = text(value, "")
    value = " ".join(value.split())
    return value if len(value) <= length else value[: length - 1] + "…"


def parse_component_statuses(values: Optional[Iterable[str]], option: str = "--component") -> Optional[Dict[str, str]]:
    """Parse repeated ID=STATUS options into {component_id: status}."""
    if not values:
        return None
    result: Dict[str, str] = {}
    for raw in values:
        sep = "=" if "=" in raw else ":" if ":" in raw else None
        if not sep:
            raise typer.BadParameter(f"'{raw}' must look like COMPONENT_ID=STATUS", param_hint=option)
        component_id, status = (part.strip() for part in raw.split(sep, 1))
        if not component_id or status not in COMPONENT_STATUSES:
            raise typer.BadParameter(
                f"'{raw}': status must be one of {', '.join(COMPONENT_STATUSES)}", param_hint=option
            )
        result[component_id] = status
    return result


def parse_future_time(value: Optional[str], option: str) -> Optional[datetime]:
    """Parse ISO 8601 or '+2h' / '+1d' (from now) into an aware UTC datetime."""
    if value is None:
        return None
    match = _FUTURE_RELATIVE.match(value.strip().lower())
    if match:
        amount, unit = int(match.group(1)), match.group(2)
        return (datetime.now(timezone.utc) + timedelta(**{_UNITS[unit]: amount})).replace(microsecond=0)
    if re.match(r"^\d+\s*[mhdw]$", value.strip().lower()):
        raise typer.BadParameter(f"'{value}' would be in the past; use '+{value}' for a time from now", param_hint=option)
    return parse_time_arg(value, option)


def parse_past_time(value: Optional[str], option: str) -> Optional[datetime]:
    """Parse ISO 8601 or relative ('2h' = 2 hours ago) and reject future times."""
    parsed = parse_time_arg(value, option)
    if parsed and parsed > datetime.now(timezone.utc) + timedelta(minutes=1):
        raise typer.BadParameter("must not be in the future", param_hint=option)
    return parsed


def iso(value: Optional[datetime]) -> Optional[str]:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def raw_json(api, method_name: str, query: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
    """
    Call an SDK endpoint and return the decoded JSON body without SDK model deserialization.

    Used where the SDK response models reject valid API data (e.g. PagePassword requires a
    write-only `password`, IncidentUpdate rejects maintenance statuses, EmailDomain recurses)
    or where the SDK lacks query params the API supports (`query`).
    """
    from pingera.exceptions import ApiException

    query = {k: v for k, v in (query or {}).items() if v is not None}
    if query:
        serialize = getattr(api, f"_{method_name}_serialize")
        method, url, headers, body, post_params = serialize(
            **kwargs, _request_auth=None, _content_type=None, _headers=None, _host_index=0
        )
        url += ("&" if "?" in url else "?") + urlencode(query)
        response = api.api_client.call_api(method, url, header_params=headers, body=body, post_params=post_params)
        response.read()
    else:
        response = getattr(api, f"{method_name}_without_preload_content")(**kwargs)

    data = response.data
    body_text = data.decode("utf-8", errors="replace") if isinstance(data, (bytes, bytearray)) else (data or "")
    if not 200 <= int(response.status) <= 299:
        raise ApiException.from_response(http_resp=response, body=body_text, data=None)
    if not body_text.strip():
        return None
    try:
        return json.loads(body_text)
    except ValueError:
        raise ValueError(f"unexpected non-JSON response: {body_text[:200]}")


def as_dict(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        value = to_plain(value)
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def component_status_map(value: Any) -> Dict[str, str]:
    """Normalize incident-update `components` (dict id->status, or list of component dicts)."""
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items() if isinstance(v, (str, int, float))}
    result = {}
    for item in as_list(value):
        item = as_dict(item)
        if item.get("id"):
            result[str(item["id"])] = text(item.get("status"))
    return result
