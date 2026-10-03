"""Tests for `bj issue create`."""

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bitbucket_jira_cli.commands import issue as issue_cmd
from bitbucket_jira_cli.main import app

runner = CliRunner()


class FakeJira:
    """Stand-in for JiraClient recording the create payload."""

    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def __aenter__(self) -> "FakeJira":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def create_issue(self, body: dict[str, Any]) -> dict[str, Any]:
        self.created.append(body)
        return {"key": "PROJ-2"}


@pytest.fixture
def fake_jira(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeJira:
    """Point the issue commands at a fake Jira and an empty config dir."""
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    client = FakeJira()
    monkeypatch.setattr(issue_cmd, "jira_client", lambda _config: client)
    return client


def _create(*extra: str) -> Any:
    return runner.invoke(
        app, ["issue", "create", "-p", "PROJ", "-s", "Write tests", "--json", *extra]
    )


def test_create_without_parent_sends_no_parent(fake_jira: FakeJira) -> None:
    """A plain create leaves the parent field out."""
    result = _create()
    assert result.exit_code == 0
    assert "parent" not in fake_jira.created[0]["fields"]


def test_create_subtask_with_parent_key(fake_jira: FakeJira) -> None:
    """--parent sends fields.parent by key, so Jira accepts a sub-task type."""
    result = _create("--type", "Subtask", "--parent", "proj-1")
    assert result.exit_code == 0
    fields = fake_jira.created[0]["fields"]
    assert fields["issuetype"] == {"name": "Subtask"}
    assert fields["parent"] == {"key": "PROJ-1"}


def test_create_story_under_epic(fake_jira: FakeJira) -> None:
    """--parent also works for a standard type under an epic."""
    result = _create("--type", "Story", "--parent", "PROJ-10")
    assert result.exit_code == 0
    assert fake_jira.created[0]["fields"]["parent"] == {"key": "PROJ-10"}


def test_create_parent_numeric_id(fake_jira: FakeJira) -> None:
    """A numeric --parent is sent as an issue id."""
    result = _create("--parent", "10001")
    assert result.exit_code == 0
    assert fake_jira.created[0]["fields"]["parent"] == {"id": "10001"}


def test_create_rejects_an_invalid_parent(fake_jira: FakeJira) -> None:
    """A value that is neither a key nor an id fails before any request."""
    result = _create("--parent", "not a key")
    assert result.exit_code == 1
    assert not fake_jira.created
