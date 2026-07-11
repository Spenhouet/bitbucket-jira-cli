"""Relative timestamp formatting, e.g. "about 2 hours ago" (gh-style)."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone

from dateutil import parser as date_parser

_MINUTE = 60
_HOUR = 3600
_DAY = 86400
_MONTH = 2592000
_YEAR = 31536000


def relative_time(value: str | None) -> str:
    """Format an ISO-8601 timestamp as a relative string; '' if unparseable."""
    if not value:
        return ""
    try:
        moment = date_parser.parse(value)
    except (ValueError, OverflowError):
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    seconds = (datetime.now(timezone.utc) - moment).total_seconds()
    if seconds < 0:
        return "just now"
    for unit, secs in (
        ("year", _YEAR),
        ("month", _MONTH),
        ("day", _DAY),
        ("hour", _HOUR),
        ("minute", _MINUTE),
    ):
        count = int(seconds // secs)
        if count >= 1:
            plural = "s" if count > 1 else ""
            about = "about " if unit in ("hour", "month", "year") else ""
            return f"{about}{count} {unit}{plural} ago"
    return "just now"
