"""Tests for `bj api`: fields, `--input` request bodies and errors."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bitbucket_jira_cli.commands import misc as misc_cmd
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import JiraConfig
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.main import app

runner = CliRunner()


class FakeClient:
    """Stand-in for the Jira client recording every raw request."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any, Any]] = []

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def raw(
        self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None
    ) -> Any:
        self.calls.append((method, path, params, json))
        return {"ok": True}


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    """Point `bj api` at a fake Jira client and a fixed config."""
    client = FakeClient()
    config = Config(jira=JiraConfig(site="https://example.atlassian.net"))
    monkeypatch.setattr(misc_cmd, "load_config", lambda: config)
    monkeypatch.setattr(misc_cmd, "jira_client", lambda _config: client)
    return client


def test_fields_become_json_body_for_post(fake: FakeClient) -> None:
    """Without --input, fields stay the JSON body of a non-GET request."""
    result = runner.invoke(
        app, ["api", "-b", "jira", "-X", "POST", "/issue/PROJ-1/comment", "-f", "body=hi"]
    )
    assert result.exit_code == 0, result.output
    assert fake.calls == [("POST", "/issue/PROJ-1/comment", None, {"body": "hi"})]


def test_input_file_is_sent_as_nested_json_body(fake: FakeClient, tmp_path: Path) -> None:
    """--input sends the file's JSON as the body, nested objects included."""
    body = {"fields": {"description": {"type": "doc", "version": 1, "content": []}}}
    body_file = tmp_path / "body.json"
    body_file.write_text(json.dumps(body), encoding="utf-8")

    result = runner.invoke(
        app, ["api", "-b", "jira", "-X", "PUT", "/issue/PROJ-1", "--input", str(body_file)]
    )

    assert result.exit_code == 0, result.output
    assert fake.calls == [("PUT", "/issue/PROJ-1", None, body)]


def test_input_reads_stdin_and_moves_fields_to_query(fake: FakeClient) -> None:
    """--input - reads the body from stdin, and fields become query parameters."""
    result = runner.invoke(
        app,
        ["api", "-b", "jira", "-X", "PUT", "/issue/PROJ-1", "--input", "-", "-f", "notify=false"],
        input='{"fields": {"summary": "New title"}}',
    )

    assert result.exit_code == 0, result.output
    assert fake.calls == [
        ("PUT", "/issue/PROJ-1", {"notify": "false"}, {"fields": {"summary": "New title"}})
    ]


def test_input_with_invalid_json_fails_without_request(fake: FakeClient, tmp_path: Path) -> None:
    """A body that is not JSON is rejected with a clear error before any request."""
    body_file = tmp_path / "body.json"
    body_file.write_text("{not json", encoding="utf-8")

    result = runner.invoke(
        app, ["api", "-b", "jira", "-X", "PUT", "/issue/PROJ-1", "--input", str(body_file)]
    )

    assert isinstance(result.exception, BjError)
    assert "--input must be JSON" in str(result.exception)
    assert fake.calls == []


def test_input_missing_file_fails_without_request(fake: FakeClient, tmp_path: Path) -> None:
    """A missing --input file is reported instead of raising a traceback."""
    result = runner.invoke(
        app,
        ["api", "-b", "jira", "-X", "PUT", "/issue/PROJ-1", "--input", str(tmp_path / "no.json")],
    )

    assert isinstance(result.exception, BjError)
    assert "Cannot read --input" in str(result.exception)
    assert fake.calls == []
