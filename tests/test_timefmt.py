"""Tests for relative-time formatting."""

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from bitbucket_jira_cli.timefmt import relative_time


def _ago(**kwargs: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(**kwargs)).isoformat()


def test_hours() -> None:
    assert relative_time(_ago(hours=2)) == "about 2 hours ago"


def test_minutes() -> None:
    assert relative_time(_ago(minutes=5)) == "5 minutes ago"


def test_days() -> None:
    assert relative_time(_ago(days=3)) == "3 days ago"


def test_singular() -> None:
    assert relative_time(_ago(days=1)) == "1 day ago"


def test_empty_and_bad_input() -> None:
    assert relative_time(None) == ""
    assert relative_time("") == ""
    assert relative_time("not-a-date") == ""


def test_recent_is_just_now() -> None:
    assert relative_time(_ago(seconds=3)) == "just now"
