"""
Helpers for parsing and formatting times in CLI arguments and output
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import typer

_RELATIVE = re.compile(r"^(\d+)\s*([mhdw])$")
_UNITS = {"m": "minutes", "h": "hours", "d": "days", "w": "weeks"}


def parse_time_arg(value: Optional[str], option_name: str = "time") -> Optional[datetime]:
    """
    Parse an ISO 8601 timestamp or a relative duration ago ("30m", "24h", "7d", "2w").

    Naive timestamps are treated as UTC.
    """
    if value is None:
        return None
    value = value.strip()
    match = _RELATIVE.match(value.lower())
    if match:
        amount, unit = int(match.group(1)), match.group(2)
        return (datetime.now(timezone.utc) - timedelta(**{_UNITS[unit]: amount})).replace(microsecond=0)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise typer.BadParameter(
            f"'{value}' is not an ISO 8601 date (e.g. 2026-01-31 or 2026-01-31T12:00:00Z) "
            "or a relative time (e.g. 30m, 24h, 7d)",
            param_hint=option_name,
        )
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def format_dt(value, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format a datetime (or ISO string) for tables; '-' when missing."""
    if not value:
        return "-"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    return value.strftime(fmt)


def format_duration(seconds: Optional[float]) -> str:
    """Compact human duration like '3d 4h', '12m 5s'."""
    if seconds is None:
        return "-"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    parts = []
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if seconds >= size:
            parts.append(f"{seconds // size}{unit}")
            seconds %= size
        if len(parts) == 2:
            break
    return " ".join(parts)
