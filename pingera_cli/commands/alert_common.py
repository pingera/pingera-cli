"""
Shared helpers for the `pngr alerts` command family (alerts, rules, channels)
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

import typer

SEVERITIES = ("low", "medium", "high", "critical")
ALERT_STATUSES = ("active", "firing", "acknowledged", "resolved", "suppressed")
CONDITIONS = ("check_failed", "check_timeout", "check_degraded", "consecutive_failures", "uptime_below_threshold")
REGION_MODES = ("any_region", "all_regions", "majority", "specific_count")
CHANNEL_TYPES = ("email", "webhook", "telegram", "max", "sms", "statuspage")
TESTABLE_CHANNEL_TYPES = ("email", "webhook", "telegram", "max")
WEBHOOK_METHODS = ("POST", "PUT", "PATCH")

SEVERITY_STYLE = {"low": "blue", "medium": "yellow", "high": "red", "critical": "bold red"}
STATUS_STYLE = {
    "firing": "bold red",
    "acknowledged": "yellow",
    "resolved": "green",
    "suppressed": "dim",
    "sent": "green",
    "pending": "yellow",
    "retrying": "yellow",
    "failed": "red",
    "cancelled": "dim",
}

_SECRET_HINTS = ("token", "secret", "password", "passwd", "key", "auth", "signature", "credential", "cookie")
_SAFE_HEADERS = ("content-type", "accept", "user-agent")
_MASK = "********"
_DURATION = re.compile(r"^(\d+)\s*([smhd]?)$")
_DURATION_UNITS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}
E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def text(value: Any, default: str = "-") -> str:
    """Render scalar API values; untyped fields may hold anything (the mock returns schema fragments)."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (str, int, float)) and value != "":
        return str(value)
    return default


def styled(value: Any, styles: Dict[str, str]) -> str:
    raw = text(value)
    style = styles.get(raw.lower())
    return f"[{style}]{raw}[/{style}]" if style else raw


def as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def parse_dt(value: Any) -> Optional[datetime]:
    """Parse API timestamps (datetime or ISO string; naive = UTC)."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def parse_seconds(value: Optional[str], option: str) -> Optional[int]:
    """Parse '300', '90s', '5m', '1h', '1d' into seconds."""
    if value is None:
        return None
    match = _DURATION.match(value.strip().lower())
    if not match:
        raise typer.BadParameter(f"'{value}' is not a duration (e.g. 300, 90s, 5m, 1h, 1d)", param_hint=option)
    return int(match.group(1)) * _DURATION_UNITS[match.group(2)]


def human_seconds(value: Any) -> str:
    if not isinstance(value, int) or isinstance(value, bool):
        return text(value)
    if value == 0:
        return "none"
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if value % size == 0:
            return f"{value // size}{unit}"
    return f"{value}s"


def parse_json_option(value: Optional[str], option: str) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    try:
        data = json.loads(value)
    except ValueError as e:
        raise typer.BadParameter(f"invalid JSON: {e}", param_hint=option)
    if not isinstance(data, dict):
        raise typer.BadParameter("must be a JSON object", param_hint=option)
    return data


def load_file(path: Optional[str], option: str = "--from-file") -> Dict[str, Any]:
    """Load a JSON/YAML object from a local file or URL."""
    if path is None:
        return {}
    from ..utils.file_utils import load_check_file

    try:
        data = load_check_file(path)
    except typer.Exit as e:
        raise typer.BadParameter(str(e.__cause__ or f"cannot read {path}"), param_hint=option)
    except Exception as e:
        raise typer.BadParameter(str(e), param_hint=option)
    if not isinstance(data, dict):
        raise typer.BadParameter("file must contain a JSON/YAML object", param_hint=option)
    return data


def check_choice(value: Optional[str], allowed, option: str) -> Optional[str]:
    if value is None:
        return None
    if value not in allowed:
        raise typer.BadParameter(f"'{value}' is not one of: {', '.join(allowed)}", param_hint=option)
    return value


def mask_url(url: Any) -> str:
    """Keep scheme and host only: webhook URLs often embed tokens in the path or query."""
    if not isinstance(url, str) or not url:
        return text(url)
    try:
        parts = urlsplit(url)
    except ValueError:
        return _MASK
    if not parts.scheme or not parts.netloc:
        return _MASK
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    hidden = (parts.path not in ("", "/")) or parts.query or parts.fragment
    return f"{parts.scheme}://{host}/{'***' if hidden else ''}"


def _is_secret_key(key: str) -> bool:
    key = key.lower()
    return any(hint in key for hint in _SECRET_HINTS)


def mask_config(config: Any) -> Dict[str, Any]:
    """Copy of a channel configuration that is safe to print (secrets and webhook URLs masked)."""
    masked: Dict[str, Any] = {}
    for key, value in as_dict(config).items():
        key = str(key)
        if key == "headers" and isinstance(value, dict):
            masked[key] = {
                str(h): (v if str(h).lower() in _SAFE_HEADERS and not _is_secret_key(str(h)) else _MASK)
                for h, v in value.items()
            }
        elif _is_secret_key(key):
            masked[key] = _MASK
        elif key == "url":
            masked[key] = mask_url(value)
        elif isinstance(value, dict):
            masked[key] = mask_config(value)
        else:
            masked[key] = value
    return masked


def channel_target(channel_type: Any, config: Any) -> str:
    """One-line, secret-free summary of where a channel delivers."""
    cfg = as_dict(config)

    def join(values: Any) -> str:
        items = [text(v) for v in as_list(values)]
        if len(items) > 3:
            return ", ".join(items[:3]) + f" (+{len(items) - 3})"
        return ", ".join(items) or "-"

    if channel_type == "email":
        return join(cfg.get("recipients"))
    if channel_type == "sms":
        return join(cfg.get("phone_numbers"))
    if channel_type == "webhook":
        method = text(cfg.get("method"), "POST").upper()
        return f"{method} {mask_url(cfg.get('url'))}"
    if channel_type in ("telegram", "max"):
        return f"chat {text(cfg.get('chat_id'))}"
    if channel_type == "statuspage":
        return f"page {text(cfg.get('page_id'))} / component {text(cfg.get('component_id'))}"
    return "-"


def pagination_line(pagination: Any, shown: int) -> Optional[str]:
    p = as_dict(pagination)
    if not p:
        return None
    total, page, pages = p.get("total"), p.get("page"), p.get("pages")
    if not all(isinstance(v, int) for v in (total, page, pages)):
        return None
    hint = " • next: --page {}".format(page + 1) if p.get("has_next") is True else ""
    return f"[dim]Showing {shown} of {total} • page {page} of {pages}{hint}[/dim]"
