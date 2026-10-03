"""Tests for `bj search`: gh-style filter flags, output, `--web`, prs and commits."""

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
        self.prs: dict[str, list[dict[str, Any]]] = {}
        self.commits: list[dict[str, Any]] = []
        self.commits_read = 0

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

    async def current_user(self) -> dict[str, Any]:
        return {"uuid": "{me}"}

    async def list_repos(self, _workspace: str, *, limit: int) -> list[dict[str, Any]]:
        return [{"slug": slug} for slug in self.prs][:limit]

    async def list_prs(
        self, workspace: str, repo_slug: str, *, query: str, sort: str, limit: int
    ) -> list[dict[str, Any]]:
        self.queries.append((f"{workspace}/{repo_slug}", query))
        return self.prs.get(repo_slug, [])[:limit]

    async def list_user_prs(
        self, workspace: str, selected_user: str, *, query: str, sort: str, limit: int
    ) -> list[dict[str, Any]]:
        self.queries.append((f"{workspace}@{selected_user}", query))
        return []

    async def iter_commits(self, _workspace: str, _repo_slug: str, *, revision: str | None) -> Any:
        for commit in self.commits:
            self.commits_read += 1
            yield commit


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
            "search",
            "code",
            "Widget",
            "-W",
            "myteam",
            "--language",
            "python",
            "--extension",
            ".py",
            "--filename",
            "src/*",
            "--repo",
            "api",
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
            "search",
            "issues",
            "--assignee",
            "@me",
            "--author",
            "abc123",
            "--state",
            "open",
            "-p",
            "PROJ",
            "-l",
            "backend",
            "-l",
            "urgent",
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


ALL_STATES = '(state = "OPEN" OR state = "MERGED" OR state = "DECLINED" OR state = "SUPERSEDED")'


def test_prs_by_author_use_one_workspace_request(fake: FakeClient) -> None:
    """--author @me goes to the workspace endpoint for the current user."""
    result = runner.invoke(
        app, ["search", "prs", "cache", "-W", "myteam", "--author", "@me", "-s", "merged"]
    )
    assert result.exit_code == 0, result.output
    assert fake.queries == [
        ("myteam@{me}", '(title ~ "cache" OR description ~ "cache") AND state = "MERGED"')
    ]


def test_prs_in_one_repo_filter_author_in_query(fake: FakeClient) -> None:
    """With --repo the author, base and head become BBQL clauses."""
    result = runner.invoke(
        app,
        ["search", "prs", "-R", "myteam/api", "--author", "{abc}", "-B", "main", "-H", "fix"],
    )
    assert result.exit_code == 0, result.output
    assert fake.queries == [
        (
            "myteam/api",
            f'{ALL_STATES} AND author.uuid = "{{abc}}" AND destination.branch.name = "main" '
            'AND source.branch.name = "fix"',
        )
    ]


def test_prs_without_author_fan_out_and_sort(fake: FakeClient) -> None:
    """Without --author every repository is queried and results are merged by update."""
    fake.prs = {
        "api": [{"id": 1, "updated_on": "2026-01-01"}, {"id": 2, "updated_on": "2026-03-01"}],
        "web": [{"id": 3, "updated_on": "2026-02-01"}],
    }
    result = runner.invoke(
        app, ["search", "prs", "-W", "myteam", "-L", "2", "--jq", "[.[].id]", "-s", "open"]
    )
    assert result.exit_code == 0, result.output
    assert sorted(fake.queries) == [
        ("myteam/api", 'state = "OPEN"'),
        ("myteam/web", 'state = "OPEN"'),
    ]
    assert result.stdout.split() == ["[", "2,", "3", "]"]


def _commit(message: str, day: str, author: str = "Jane Doe <jane@example.com>") -> Any:
    return {
        "hash": "a" * 40,
        "message": message,
        "date": f"{day}T10:00:00+00:00",
        "author": {"raw": author, "user": {"uuid": "{me}" if "Jane" in author else "{x}"}},
    }


def test_commits_filter_message_and_author(fake: FakeClient) -> None:
    """Commits are matched on message text and author, case-insensitively."""
    fake.commits = [
        _commit("Fix cache bug", "2026-03-03"),
        _commit("Fix cache leak", "2026-03-02", author="Max Mustermann <max@example.com>"),
        _commit("Add docs", "2026-03-01"),
    ]
    result = runner.invoke(
        app,
        [
            "search",
            "commits",
            "CACHE",
            "-R",
            "myteam/api",
            "--author",
            "jane",
            "--jq",
            "[.[].message]",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Fix cache bug" in result.stdout
    assert "leak" not in result.stdout
    me = runner.invoke(
        app, ["search", "commits", "-R", "myteam/api", "--author", "@me", "--jq", "length"]
    )
    assert me.stdout.strip() == "2"


def test_commits_stop_at_since_and_limit(fake: FakeClient) -> None:
    """--since and --limit stop reading the history early."""
    fake.commits = [
        _commit("one", "2026-03-03"),
        _commit("two", "2026-03-02"),
        _commit("three", "2026-02-01"),
        _commit("four", "2026-01-01"),
    ]
    result = runner.invoke(
        app,
        ["search", "commits", "-R", "myteam/api", "--since", "2026-03-01", "--jq", "length"],
    )
    assert result.stdout.strip() == "2"
    assert fake.commits_read == 3
    fake.commits_read = 0
    limited = runner.invoke(app, ["search", "commits", "-R", "myteam/api", "-L", "1"])
    assert limited.exit_code == 0, limited.output
    assert fake.commits_read == 1
