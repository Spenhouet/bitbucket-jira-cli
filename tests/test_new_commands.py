"""Tests for the commands added to mirror gh's surface."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bitbucket_jira_cli.main import _expand_alias
from bitbucket_jira_cli.main import app

runner = CliRunner()

NEW_GROUPS = [
    "release", "variable", "config", "search",
    "ssh-key", "snippet", "ruleset", "board", "alias", "status",
]


@pytest.mark.parametrize("name", NEW_GROUPS)
def test_group_registered(name: str) -> None:
    """Every new command appears in the top-level help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert name in result.stdout


def test_config_set_get_list_roundtrip(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """Set persists a value that config get and list read back."""
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    assert runner.invoke(app, ["config", "set", "git_protocol", "ssh"]).exit_code == 0
    got = runner.invoke(app, ["config", "get", "git_protocol"])
    assert got.exit_code == 0
    assert "ssh" in got.stdout
    listing = runner.invoke(app, ["config", "list"])
    assert "git_protocol" in listing.stdout


def test_config_set_rejects_invalid_value(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """A value outside the schema's allowed set is rejected."""
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["config", "set", "git_protocol", "carrier-pigeon"])
    assert result.exit_code == 1


def test_config_set_unknown_key(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """An unknown key path is rejected rather than silently added."""
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["config", "set", "bitbucket.nope", "x"])
    assert result.exit_code == 1


def test_alias_roundtrip_and_expansion(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """An alias set via the CLI is expanded by _expand_alias."""
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    assert runner.invoke(app, ["alias", "set", "prs", "pr list --state open"]).exit_code == 0
    assert _expand_alias(["prs", "--json"]) == ["pr", "list", "--state", "open", "--json"]
    # A non-alias passes through untouched.
    assert _expand_alias(["pr", "list"]) == ["pr", "list"]


def test_alias_cannot_shadow_builtin(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """Aliases may not shadow a built-in command name."""
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["alias", "set", "pr", "issue list"])
    assert result.exit_code == 1
