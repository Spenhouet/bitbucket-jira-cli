"""Smoke tests for the CLI scaffold."""

from typer.testing import CliRunner

import bitbucket_jira_cli
from bitbucket_jira_cli.main import app

runner = CliRunner()


def test_package_imports() -> None:
    """The package imports and exposes a version string."""
    assert isinstance(bitbucket_jira_cli.__version__, str)


def test_help_lists_command_groups() -> None:
    """`bj --help` renders and lists the top-level command groups."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for group in ("auth", "repo", "pr", "issue", "pipeline"):
        assert group in result.stdout


def test_version_flag() -> None:
    """`bj --version` prints the distribution name and exits cleanly."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "bitbucket-jira-cli" in result.stdout
