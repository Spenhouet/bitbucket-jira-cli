"""Tests for the shared console output helpers."""

import io
import sys

import pytest
from rich.console import Console

from bitbucket_jira_cli import ui


def _cp1252_stream() -> io.TextIOWrapper:
    """A text stream like a Windows console or pipe on a cp1252 code page."""
    return io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")


def test_unsafe_stream_crashes_on_check_mark(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the guard, a cp1252 stdout cannot print the status symbols."""
    monkeypatch.setattr(sys, "stdout", _cp1252_stream())
    # A fresh console, so the unwritten text does not stay in the shared ui.console buffer.
    with pytest.raises(UnicodeEncodeError):
        Console().print("✓ logged in")


def test_ensure_safe_output_replaces_unencodable_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After the guard, unencodable characters print as '?' instead of crashing."""
    stdout = _cp1252_stream()
    stderr = _cp1252_stream()
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    ui.ensure_safe_output()
    ui.console.print("✓ logged in")
    ui.success("approved")

    stdout.flush()
    stderr.flush()
    assert stdout.buffer.getvalue().decode("cp1252").strip() == "? logged in"
    assert stderr.buffer.getvalue().decode("cp1252").strip() == "? approved"


def test_ensure_safe_output_ignores_streams_without_reconfigure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replaced streams without `reconfigure` (e.g. StringIO) are left alone."""
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    monkeypatch.setattr(sys, "stderr", io.StringIO())
    ui.ensure_safe_output()
