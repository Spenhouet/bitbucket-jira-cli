"""Tests for `bj search`: gh-style filter flags, output, `--web`, prs and commits."""

import asyncio
import json
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from bitbucket_jira_cli.api.bitbucket import BASE_URL
from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.commands import search as search_cmd
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import JiraConfig
from bitbucket_jira_cli.errors import ApiError
from bitbucket_jira_cli.main import app

runner = CliRunner()


class FakeClient:
    """Stand-in for the Bitbucket and Jira clients recording the queries sent."""

    def __init__(self, code_hits: list[dict[str, Any]] | None = None) -> None:
        self.queries: list[tuple[str, str]] = []
        self.code_hits = code_hits or []
        self.code_filters: list[dict[str, Any] | None] = []
        self.code_error: Exception | None = None
        self.prs: dict[str, list[dict[str, Any]]] = {}
        self.commits: list[dict[str, Any]] = []
        self.commits_read = 0

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def search_code(
        self, workspace: str, term: str, *, filters: dict[str, Any] | None, limit: int
    ) -> list[Any]:
        self.queries.append((workspace, term))
        self.code_filters.append(filters)
        if self.code_error:
            raise self.code_error
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


def _hit(path: str, repo: str = "api") -> dict[str, Any]:
    return {
        "path": path,
        "repository": {"ns": "myteam", "name": repo},
        "matched_chunks": [
            {
                "source_code": "import os\nclass Widget:\n    widget_count = 0\n",
                "line_range": {"start": 1, "end": 3},
                "matched_line_numbers": [2],
                "matched_ranges": [[2, 6, 12]],
            }
        ],
    }


def test_code_flags_become_filters(fake: FakeClient) -> None:
    """--language, --extension, --filename and --repo become code search filters."""
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
    assert fake.queries == [("myteam", "Widget")]
    assert fake.code_filters == [
        {
            "and": [
                {"attribute": "repository", "eq": "api"},
                {"attribute": "language", "eq": "python"},
                {"attribute": "extension", "eq": "py"},
                {"attribute": "path", "wildcard": "src/*"},
            ]
        }
    ]


def test_code_query_modifiers_become_filters(fake: FakeClient) -> None:
    """repo:, lang:, ext: and path: in the query still work, as filters."""
    result = runner.invoke(app, ["search", "code", "repo:web-* new Widget ext:ts", "-W", "myteam"])
    assert result.exit_code == 0, result.output
    assert fake.queries == [("myteam", "new Widget")]
    assert fake.code_filters == [
        {
            "and": [
                {"attribute": "repository", "wildcard": "web-*"},
                {"attribute": "extension", "eq": "ts"},
            ]
        }
    ]


def test_code_without_filters_sends_none(fake: FakeClient) -> None:
    result = runner.invoke(app, ["search", "code", "Widget", "-W", "myteam"])
    assert result.exit_code == 0, result.output
    assert fake.code_filters == [None]


def test_code_needs_a_search_term(fake: FakeClient) -> None:
    """A query of only modifiers is rejected before any request."""
    result = runner.invoke(app, ["search", "code", "lang:go", "-W", "myteam"])
    assert result.exit_code != 0
    assert "search term" in str(result.exception)
    assert fake.queries == []


def test_code_repo_with_workspace_sets_workspace(fake: FakeClient) -> None:
    """--repo WORKSPACE/REPO picks the workspace like gh's OWNER/REPO."""
    result = runner.invoke(app, ["search", "code", "Widget", "-R", "otherteam/api"])
    assert result.exit_code == 0, result.output
    assert fake.queries == [("otherteam", "Widget")]
    assert fake.code_filters == [{"attribute": "repository", "eq": "api"}]


def test_code_output_shows_repo_and_matching_lines(fake: FakeClient) -> None:
    """Each hit shows its repository, path, and the lines that matched."""
    fake.code_hits = [_hit("a.py"), _hit("b.py", repo="web")]
    result = runner.invoke(app, ["search", "code", "Widget", "-W", "myteam"])
    assert result.exit_code == 0, result.output
    assert "myteam/api a.py" in result.output
    assert "myteam/web b.py" in result.output
    assert "2: class Widget:" in result.output
    # Not marked by Bitbucket (no whole word), but contains the term.
    assert "3: widget_count = 0" in result.output
    assert "import os" not in result.output


def test_code_forbidden_explains_the_token(fake: FakeClient) -> None:
    """A 403 says which credential code search needs."""
    fake.code_error = ApiError("Bitbucket", 403, "Forbidden")
    result = runner.invoke(app, ["search", "code", "Widget", "-W", "myteam"])
    assert result.exit_code != 0
    assert "app passwords" in str(result.exception)


def test_search_code_follows_the_cursor_and_attaches_repositories() -> None:
    """The client posts to codesearch, pages with the cursor and joins each file's repository."""
    bodies: list[dict[str, Any]] = []
    pages = [
        {
            "id": "req-1",
            "pagination": {"has_more": True, "next_cursor": "c1"},
            "repositories": [{"id": "r1", "ns": "myteam", "name": "api"}],
            "matched_files": [{"path": "a.py", "repositoryId": "r1"}],
        },
        {
            "id": "req-1",
            "pagination": {"has_more": False, "next_cursor": None},
            "repositories": [{"id": "r2", "ns": "myteam", "name": "web"}],
            "matched_files": [{"path": "b.py", "repositoryId": "r2"}],
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/2.0/workspaces/myteam/codesearch"
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=pages[len(bodies) - 1])

    async def run() -> list[dict[str, Any]]:
        client = BitbucketClient("Basic dummy")
        client._client = httpx.AsyncClient(
            base_url=BASE_URL, transport=httpx.MockTransport(handler)
        )
        async with client:
            return await client.search_code(
                "myteam", "Widget", filters={"attribute": "language", "eq": "python"}, limit=5
            )

    files = asyncio.run(run())
    assert [(f["path"], f["repository"]["name"]) for f in files] == [
        ("a.py", "api"),
        ("b.py", "web"),
    ]
    assert bodies[0] == {
        "query": {"search_term": "Widget", "filters": {"attribute": "language", "eq": "python"}},
        "config": {"max_results": 5},
    }
    assert bodies[1]["request_id"] == "req-1"
    assert bodies[1]["pagination"] == {"next_cursor": "c1"}
    assert bodies[1]["config"] == {"max_results": 4}


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
