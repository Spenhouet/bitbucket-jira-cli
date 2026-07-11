"""Tests for interaction helpers that don't require a TTY."""

import pytest

from bitbucket_jira_cli import interaction
from bitbucket_jira_cli.errors import BjError


def test_prompt_disabled_forces_non_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BJ_PROMPT_DISABLED", "1")
    assert interaction.is_interactive() is False


def test_require_input_returns_value() -> None:
    assert interaction.require_input("hi", flag="--body", label="Body") == "hi"


def test_require_input_errors_when_non_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BJ_PROMPT_DISABLED", "1")
    with pytest.raises(BjError, match="must provide --title"):
        interaction.require_input(None, flag="--title", label="Title")


def test_confirm_proceeds_when_non_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BJ_PROMPT_DISABLED", "1")
    assert interaction.confirm("Delete?", yes=False) is True


def test_confirm_yes_short_circuits() -> None:
    assert interaction.confirm("Delete?", yes=True) is True
