"""Tests for `bj search`: gh-style filter flags, code hit output, and `--web`."""

from typing import Any

import pytest
from typer.testing import CliRunner

from bitbucket_jira_cli.commands import search as search_cmd
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import JiraConfig
from bitbucket_jira_cli.main import app

runner = CliRunner()


class FakeClient:
    """Stand-in for the Bitbucket and Jira clients recording the queries sent."""

    def __init__(self, code_hits: list[dict[str, Any]] | None = None) -> None:
        self.queries: list[tuple[str, str]] = []
        self.code_hits = code_hits or []

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def search_code(self, workspace: str, query: str, *, limit: int) -> list[Any]:
        self.queries.append((workspace, query))
        return self.code_hits[:limit]

    async def search(self, jql: str, *, limit: int) -> list[Any]:
        self.queries.append(("jira", jql))
        return []


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    """Point the search commands at a fake client and a fixed config."""
    client = FakeClient()
    config = Config(jira=JiraConfig(site="https://example.atlassian.net"))
    monkeypatch.setattr(search_cmd, "load_config", lambda: config)
    monkeypatch.setattr(search_cmd, "_bb", lambda _config: client)
    monkeypatch.setattr(search_cmd, "jira_client", lambda _config: client)
    return client


def _hit(path: str, href: str, repo: str | None = None) -> dict[str, Any]:
    commit: dict[str, Any] = {"repository": {"full_name": repo}} if repo else {}
    return {
        "file": {"path": path, "commit": commit, "links": {"self": {"href": href}}},
        "content_matches": [
            {
                "lines": [
                    {"line": 1, "segments": [{"text": "import os"}]},
                    {
                        "line": 2,
                        "segments": [
                            {"text": "class "},
                            {"text": "Widget", "match": True},
                            {"text": ":"},
                        ],
                    },
                ]
            }
        ],
    }


def test_code_flags_become_search_modifiers(fake: FakeClient) -> None:
    """--language, --extension, --filename and --repo map to Bitbucket modifiers."""
    result = runner.invoke(
        app,
        [
            "search", "code", "Widget", "-W", "myteam",
            "--language", "python", "--extension", ".py", "--filename", "src/*",
            "--repo", "api",
        ],
    )
    assert result.exit_code == 0, result.output
    assert fake.queries == [("myteam", "Widget repo:api lang:python ext:py path:src/*")]


def test_code_repo_with_workspace_sets_workspace(fake: FakeClient) -> None:
    """--repo WORKSPACE/REPO picks the workspace like gh's OWNER/REPO."""
    result = runner.invoke(app, ["search", "code", "Widget", "-R", "otherteam/api"])
    assert result.exit_code == 0, result.output
    assert fake.queries == [("otherteam", "Widget repo:api")]


def test_code_output_shows_repo_and_matching_lines(fake: FakeClient) -> None:
    """Each hit shows its repository, path, and the lines that matched."""
    fake.code_hits = [
        _hit("a.py", "https://api.bitbucket.org/2.0/x", repo="myteam/api"),
        # No repository object: fall back to the repository in the file's link.
        _hit("b.py", "https://api.bitbucket.org/2.0/repositories/myteam/web/src/abc/b.py"),
    ]
    result = runner.invoke(app, ["search", "code", "Widget", "-W", "myteam"])
    assert result.exit_code == 0, result.output
    assert "myteam/api a.py" in result.output
    assert "myteam/web b.py" in result.output
    assert "2: class Widget:" in result.output
    assert "import os" not in result.output


def test_code_has_no_w_workspace_flag(fake: FakeClient) -> None:
    """-w is not --workspace on search, since it means --web in gh and elsewhere in bj."""
    result = runner.invoke(app, ["search", "code", "Widget", "-w", "myteam"])
    assert result.exit_code != 0
    assert fake.queries == []


def test_issues_filters_build_jql(fake: FakeClient) -> None:
    """gh-style flags alone build a bounded JQL query."""
    result = runner.invoke(
        app,
        [
            "search", "issues", "--assignee", "@me", "--author", "abc123",
            "--state", "open", "-p", "PROJ", "-l", "backend", "-l", "urgent",
        ],
    )
    assert result.exit_code == 0, result.output
    assert fake.queries == [
        (
            "jira",
            'project = "PROJ" AND assignee = currentUser() AND reporter = "abc123" '
            'AND statusCategory != Done AND labels = "backend" AND labels = "urgent" '
            "ORDER BY updated DESC",
        )
    ]


def test_issues_flags_combine_with_jql_and_keep_order(fake: FakeClient) -> None:
    """Flags are ANDed onto the JQL query and its ORDER BY is kept at the end."""
    result = runner.invoke(
        app,
        ["search", "issues", "text ~ cache OR summary ~ db order by created", "-s", "closed"],
    )
    assert result.exit_code == 0, result.output
    assert fake.queries == [
        ("jira", "(text ~ cache OR summary ~ db) AND statusCategory = Done ORDER BY created")
    ]


def test_issues_without_query_or_filters_fails(fake: FakeClient) -> None:
    """An unbounded search is rejected before calling Jira."""
    result = runner.invoke(app, ["search", "issues"])
    assert result.exit_code == 1
    assert fake.queries == []


def test_issues_web_opens_jira_search(fake: FakeClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """--web opens the Jira issue navigator with the built JQL."""
    opened: list[str] = []
    monkeypatch.setattr(search_cmd.webbrowser, "open", opened.append)
    result = runner.invoke(app, ["search", "issues", "-p", "PROJ", "--web"])
    assert result.exit_code == 0, result.output
    assert opened == [
        "https://example.atlassian.net/issues/?jql="
        "project%20%3D%20%22PROJ%22%20ORDER%20BY%20updated%20DESC"
    ]
    assert fake.queries == []
