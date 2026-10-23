"""Tests for listing Jira boards and sprints through the agile API."""

from typing import Any

import httpx
import pytest
from rich.console import Console
from typer.testing import CliRunner

from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.api.jira import JiraClient
from bitbucket_jira_cli.commands import board as board_cmd
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import JiraConfig
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.main import app

runner = CliRunner()

SITE = "https://ex.atlassian.net/rest/api/3"


def _client(total: int, seen: list[httpx.Request], page_size: int = 50) -> JiraClient:
    """A JiraClient whose agile endpoints serve ``total`` items in pages of ``page_size``."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        start = int(request.url.params.get("startAt", 0))
        end = min(start + page_size, total)
        values = [{"id": i, "name": f"Item {i}"} for i in range(start, end)]
        return httpx.Response(
            200,
            json={
                "startAt": start,
                "maxResults": page_size,
                "isLast": end >= total,
                "values": values,
            },
        )

    client = JiraClient(SITE, "Basic dummy")
    client._client = httpx.AsyncClient(base_url=SITE, transport=httpx.MockTransport(handler))
    return client


async def _sprints(total: int, seen: list[httpx.Request]) -> list[dict[str, Any]]:
    async with _client(total, seen) as client:
        return await client.list_sprints(7)


async def _boards(
    total: int, seen: list[httpx.Request], project: str | None = None
) -> list[dict[str, Any]]:
    async with _client(total, seen) as client:
        return await client.list_boards(project=project)


def test_list_sprints_follows_every_page() -> None:
    seen: list[httpx.Request] = []
    sprints = run(_sprints(75, seen))
    assert [s["id"] for s in sprints] == list(range(75))
    assert [r.url.params["startAt"] for r in seen] == ["0", "50"]


def test_list_sprints_single_page_makes_one_request() -> None:
    seen: list[httpx.Request] = []
    run(_sprints(3, seen))
    assert len(seen) == 1


def test_list_boards_follows_every_page() -> None:
    seen: list[httpx.Request] = []
    boards = run(_boards(120, seen))
    assert len(boards) == 120
    assert [r.url.params["startAt"] for r in seen] == ["0", "50", "100"]


def test_list_boards_keeps_project_filter_on_every_page() -> None:
    seen: list[httpx.Request] = []
    run(_boards(60, seen, project="PROJ"))
    assert [r.url.params["projectKeyOrId"] for r in seen] == ["PROJ", "PROJ"]


def test_empty_page_without_is_last_stops() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"values": [], "isLast": False})

    async def _go() -> list[dict[str, Any]]:
        client = JiraClient(SITE, "Basic dummy")
        client._client = httpx.AsyncClient(base_url=SITE, transport=httpx.MockTransport(handler))
        async with client:
            return await client.list_sprints(7)

    assert run(_go()) == []


def test_list_sprints_passes_state_filter() -> None:
    seen: list[httpx.Request] = []

    async def _go() -> list[dict[str, Any]]:
        async with _client(1, seen) as client:
            return await client.list_sprints(7, state="active,future")

    run(_go())
    assert seen[0].url.params["state"] == "active,future"


def test_list_sprints_without_state_sends_no_filter() -> None:
    seen: list[httpx.Request] = []
    run(_sprints(1, seen))
    assert "state" not in seen[0].url.params


def test_sprints_command_forwards_state(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []
    config = Config(jira=JiraConfig(site="https://example.atlassian.net"))
    monkeypatch.setattr(board_cmd, "load_config", lambda: config)
    monkeypatch.setattr(board_cmd, "jira_client", lambda _config: _client(1, seen))

    result = runner.invoke(app, ["board", "sprints", "7", "--state", "active"])

    assert result.exit_code == 0, result.output
    assert seen[0].url.params["state"] == "active"
    assert "Item 0" in result.output


def _issue(key: str, status_id: str, summary: str = "Thing") -> dict[str, Any]:
    return {"key": key, "fields": {"summary": summary, "status": {"id": status_id}}}


CONFIGURATION = {
    "columnConfig": {
        "columns": [
            {"name": "To Do", "statuses": [{"id": "1"}]},
            {"name": "Doing", "statuses": [{"id": "3"}, {"id": "4"}], "max": 1},
            {"name": "Done", "statuses": [{"id": "5"}]},
        ]
    }
}


def test_group_by_column_follows_status_mapping_and_drops_unmapped() -> None:
    issues = [_issue("P-1", "3"), _issue("P-2", "1"), _issue("P-3", "4"), _issue("P-4", "9")]

    columns = board_cmd.group_by_column(CONFIGURATION, issues)

    assert [(c["name"], [i["key"] for i in c["issues"]]) for c in columns] == [
        ("To Do", ["P-2"]),
        ("Doing", ["P-1", "P-3"]),
        ("Done", []),
    ]
    assert columns[1]["max"] == 1


def test_list_board_issues_pages_until_total() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        start = int(request.url.params["startAt"])
        page = [_issue(f"P-{i}", "1") for i in range(start, min(start + 50, 120))]
        return httpx.Response(200, json={"startAt": start, "total": 120, "issues": page})

    async def _go() -> list[dict[str, Any]]:
        client = JiraClient(SITE, "Basic dummy")
        client._client = httpx.AsyncClient(base_url=SITE, transport=httpx.MockTransport(handler))
        async with client:
            return await client.list_board_issues(7, jql="sprint = 3", limit=500)

    issues = run(_go())
    assert len(issues) == 120
    assert [r.url.params["startAt"] for r in seen] == ["0", "50", "100"]
    assert {r.url.path for r in seen} == {"/rest/agile/1.0/board/7/issue"}
    assert seen[0].url.params["jql"] == "sprint = 3"


def _board_client(
    board_type: str,
    seen: list[httpx.Request],
    *,
    sprints: httpx.Response | None = None,
    configuration: dict[str, Any] | None = None,
    boards: list[dict[str, Any]] | None = None,
) -> JiraClient:
    """A JiraClient serving one board, its configuration, sprints and issues."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path.endswith("/rest/agile/1.0/board"):
            return httpx.Response(200, json={"isLast": True, "values": boards or []})
        if path.endswith("/configuration"):
            return httpx.Response(200, json=configuration or CONFIGURATION)
        if path.endswith("/sprint"):
            return sprints or httpx.Response(200, json={"isLast": True, "values": []})
        if path.endswith("/issue"):
            issues = [_issue("P-1", "1", "Write [docs]"), _issue("P-2", "3")]
            return httpx.Response(200, json={"total": 2, "issues": issues})
        return httpx.Response(200, json={"id": 7, "name": "Team board", "type": board_type})

    client = JiraClient(SITE, "Basic dummy")
    client._client = httpx.AsyncClient(base_url=SITE, transport=httpx.MockTransport(handler))
    return client


def _view(
    monkeypatch: pytest.MonkeyPatch,
    client: JiraClient,
    *args: str,
    board: str | None = "7",
    default_board: int | None = None,
) -> Any:
    config = Config(jira=JiraConfig(site="https://example.atlassian.net", board=default_board))
    monkeypatch.setattr(board_cmd, "load_config", lambda: config)
    monkeypatch.setattr(board_cmd, "jira_client", lambda _config: client)
    board_args = [board] if board else []
    return runner.invoke(app, ["board", "view", *board_args, *args])


def _issue_request(seen: list[httpx.Request]) -> httpx.Request:
    return next(r for r in seen if r.url.path.endswith("/issue"))


def test_view_scrum_board_shows_active_sprint(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []
    active = httpx.Response(200, json={"isLast": True, "values": [{"id": 42, "name": "Sprint 9"}]})
    client = _board_client("scrum", seen, sprints=active)

    result = _view(monkeypatch, client)

    assert result.exit_code == 0, result.output
    assert _issue_request(seen).url.params["jql"] == "(sprint in (42))"
    assert "Sprint 9" in result.output
    assert "Write [docs]" in result.output
    assert "Doing (1/1)" in result.output


def test_view_scrum_board_without_active_sprint_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    result = _view(monkeypatch, _board_client("scrum", seen))

    assert isinstance(result.exception, BjError)
    assert "no active sprint" in str(result.exception)


UNSUPPORTED = httpx.Response(400, json={"errorMessages": ["The board does not support sprints"]})


def test_view_team_board_without_sprints_hides_old_done(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []
    client = _board_client("simple", seen, sprints=UNSUPPORTED)

    result = _view(monkeypatch, client)

    assert result.exit_code == 0, result.output
    assert _issue_request(seen).url.params["jql"] == (
        "(statusCategory != Done OR statusCategoryChangedDate >= -14d)"
    )


def test_view_done_days_zero_shows_all_done(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []
    client = _board_client("simple", seen, sprints=UNSUPPORTED)

    result = _view(monkeypatch, client, "--done-days", "0")

    assert result.exit_code == 0, result.output
    assert "jql" not in _issue_request(seen).url.params


def test_view_links_issue_keys_to_jira(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []
    client = _board_client("kanban", seen)
    monkeypatch.setattr("bitbucket_jira_cli.ui.console", Console(force_terminal=True))
    monkeypatch.setattr("bitbucket_jira_cli.render.console", Console(force_terminal=True))

    result = _view(monkeypatch, client)

    assert result.exit_code == 0, result.output
    assert "https://example.atlassian.net/browse/P-1" in result.output


def test_view_kanban_applies_sub_filter_and_jql(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []
    configuration = {**CONFIGURATION, "subQuery": {"query": "resolution = EMPTY"}}
    client = _board_client("kanban", seen, configuration=configuration)

    result = _view(monkeypatch, client, "--jql", "assignee = currentUser()")

    assert result.exit_code == 0, result.output
    assert not any(r.url.path.endswith("/sprint") for r in seen)
    assert (
        _issue_request(seen).url.params["jql"]
        == "(resolution = EMPTY) AND (assignee = currentUser())"
    )


def test_view_explicit_sprint_skips_active_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    result = _view(monkeypatch, _board_client("scrum", seen), "--sprint", "5", "--json")

    assert result.exit_code == 0, result.output
    assert not any(r.url.path.endswith("/sprint") for r in seen)
    assert _issue_request(seen).url.params["jql"] == "(sprint in (5))"
    assert '"Doing"' in result.output


def test_view_uses_configured_default_board(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    result = _view(monkeypatch, _board_client("kanban", seen), board=None, default_board=7)

    assert result.exit_code == 0, result.output
    assert _issue_request(seen).url.path == "/rest/agile/1.0/board/7/issue"


def test_view_uses_board_of_branch_project(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []
    monkeypatch.setattr(board_cmd, "current_branch", lambda: "feature/proj-42-thing")
    client = _board_client("kanban", seen, boards=[{"id": 7, "name": "Team board"}])

    result = _view(monkeypatch, client, board=None)

    assert result.exit_code == 0, result.output
    assert seen[0].url.params["projectKeyOrId"] == "PROJ"
    assert _issue_request(seen).url.path == "/rest/agile/1.0/board/7/issue"


def test_view_branch_project_with_several_boards_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []
    monkeypatch.setattr(board_cmd, "current_branch", lambda: "PROJ-42")
    boards = [{"id": 7, "name": "Team board"}, {"id": 8, "name": "Other board"}]

    result = _view(monkeypatch, _board_client("kanban", seen, boards=boards), board=None)

    assert isinstance(result.exception, BjError)
    assert "7 (Team board), 8 (Other board)" in str(result.exception)


def test_view_without_board_or_branch_key_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []
    monkeypatch.setattr(board_cmd, "current_branch", lambda: "main")

    result = _view(monkeypatch, _board_client("kanban", seen), board=None)

    assert isinstance(result.exception, BjError)
    assert "No board given" in str(result.exception)


def test_view_mine_filters_to_current_user(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    result = _view(monkeypatch, _board_client("kanban", seen), "--mine")

    assert result.exit_code == 0, result.output
    assert _issue_request(seen).url.params["jql"] == "(assignee = currentUser())"
