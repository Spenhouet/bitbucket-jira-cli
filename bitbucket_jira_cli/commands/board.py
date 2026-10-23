"""`bj board` - Jira Software boards and sprints (the gh project analog)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any

import httpx
import typer

from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import jira_browse_url
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.errors import ApiError
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.git import current_branch
from bitbucket_jira_cli.git import parse_branch_key
from bitbucket_jira_cli.interaction import paged
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.render import render_board
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import err_console

if TYPE_CHECKING:
    from bitbucket_jira_cli.api.jira import JiraClient
    from bitbucket_jira_cli.config import Config

board_app = typer.Typer(
    help="Work with Jira boards and sprints (needs an unscoped Jira token).",
    no_args_is_help=True,
)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]


@board_app.command(name="list")
def list_boards(
    project: Annotated[
        str | None, typer.Option("--project", "-p", help="Filter by project key.")
    ] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List Jira boards."""
    config = load_config()

    async def _run() -> list[dict[str, Any]]:
        async with jira_client(config) as client:
            return await client.list_boards(project=project)

    boards = run_with_status("Loading boards…", _run())
    if emit(boards, as_json=as_json, jq=jq):
        return
    if not boards:
        console.print("[dim]No boards.[/dim]")
    for board in boards:
        kind = board.get("type", "")
        console.print(f"[cyan]{board.get('id')}[/cyan] {board.get('name', '')} [dim]{kind}[/dim]")


@board_app.command()
def sprints(
    board_id: Annotated[int, typer.Argument(help="Board id (from `board list`).")],
    state: Annotated[
        str | None,
        typer.Option(
            "--state",
            "-s",
            help="Only sprints in these states: active, future, closed (comma-separated).",
        ),
    ] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List a board's sprints."""
    config = load_config()

    async def _run() -> list[dict[str, Any]]:
        async with jira_client(config) as client:
            return await client.list_sprints(board_id, state=state)

    sprint_list = run_with_status("Loading sprints…", _run())
    if emit(sprint_list, as_json=as_json, jq=jq):
        return
    if not sprint_list:
        console.print("[dim]No sprints.[/dim]")
    for sprint in sprint_list:
        state = sprint.get("state", "")
        name = sprint.get("name", "")
        console.print(f"[cyan]{sprint.get('id')}[/cyan] {name} [dim]{state}[/dim]")


BOARD_FIELDS = ["summary", "status", "assignee", "issuetype", "priority"]


def group_by_column(
    configuration: dict[str, Any], issues: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Place each issue in the board column its status is mapped to.

    Issues whose status maps to no column are not on the board, so they are dropped.
    """
    columns: list[dict[str, Any]] = []
    by_status: dict[str, dict[str, Any]] = {}
    for column in configuration.get("columnConfig", {}).get("columns", []):
        entry = {
            "name": column.get("name", ""),
            "min": column.get("min"),
            "max": column.get("max"),
            "issues": [],
        }
        columns.append(entry)
        for status in column.get("statuses", []):
            by_status[str(status.get("id"))] = entry
    for issue in issues:
        status_id = str(issue.get("fields", {}).get("status", {}).get("id"))
        if status_id in by_status:
            by_status[status_id]["issues"].append(issue)
    return columns


def _and_jql(*clauses: str | None) -> str | None:
    parts = [f"({clause})" for clause in clauses if clause]
    return " AND ".join(parts) or None


def _recent_done_jql(board: dict[str, Any], done_days: int | None) -> str | None:
    """JQL that drops issues done longer ago than ``done_days``.

    Team-managed boards hide done issues after 14 days by default. The setting is
    not exposed through the API, so the default is assumed rather than read.
    """
    if done_days is None:
        done_days = 14 if board.get("type") == "simple" else 0
    if done_days <= 0:
        return None
    return f"statusCategory != Done OR statusCategoryChangedDate >= -{done_days}d"


async def _active_sprints(client: JiraClient, board_id: int) -> list[dict[str, Any]] | None:
    """Active sprints of a board, or None when the board has sprints turned off.

    Team-managed ("simple") boards can go either way and only say so through a 400.
    """
    try:
        return await client.list_sprints(board_id, state="active")
    except ApiError as exc:
        if exc.status == httpx.codes.BAD_REQUEST:
            return None
        raise


async def _resolve_board_id(client: JiraClient, board_id: int | None, config: Config) -> int:
    """The given board, else the configured default, else the only board of the branch's project."""
    if board_id is not None:
        return board_id
    if config.jira.board is not None:
        return config.jira.board
    branch = current_branch()
    key = parse_branch_key(branch, config.branch_key) if branch else None
    if not key:
        msg = (
            "No board given. Pass a board id, set a default with "
            "`bj config set jira.board <id>`, or run on a branch named after a Jira issue."
        )
        raise BjError(msg)
    project = key.split("-", 1)[0]
    boards = await client.list_boards(project=project)
    if len(boards) == 1:
        return int(boards[0]["id"])
    if not boards:
        msg = f"Project {project} (from branch {branch}) has no board."
        raise BjError(msg)
    choices = ", ".join(f"{b.get('id')} ({b.get('name', '')})" for b in boards)
    msg = (
        f"Project {project} has several boards: {choices}. Pass one, or set a default "
        "with `bj config set jira.board <id>`."
    )
    raise BjError(msg)


async def _sprint_jql(
    client: JiraClient, board: dict[str, Any], sprint: int | None
) -> tuple[str | None, list[dict[str, Any]]]:
    """JQL limiting the board to one sprint, plus the active sprints it picked by default."""
    if sprint is not None:
        return f"sprint in ({sprint})", []
    if board.get("type") == "kanban":
        return None, []
    active = await _active_sprints(client, board["id"])
    if active is None:
        return None, []
    if not active:
        msg = (
            f"Board {board['id']} has no active sprint. Pick one with --sprint "
            f"(see `bj board sprints {board['id']}`)."
        )
        raise BjError(msg)
    return f"sprint in ({', '.join(str(s['id']) for s in active)})", active


@board_app.command()
def view(
    board_id: Annotated[
        int | None,
        typer.Argument(
            help="Board id (from `board list`). Defaults to jira.board in the config, "
            "else the board of the current branch's project.",
            show_default=False,
        ),
    ] = None,
    sprint: Annotated[
        int | None,
        typer.Option(
            "--sprint",
            help="Sprint id (from `board sprints`). Boards with sprints default to the active one.",
        ),
    ] = None,
    mine: Annotated[bool, typer.Option("--mine", help="Only show issues assigned to you.")] = False,
    jql: Annotated[
        str | None, typer.Option("--jql", help="Only show issues matching this JQL filter.")
    ] = None,
    done_days: Annotated[
        int | None,
        typer.Option(
            "--done-days",
            help="Hide issues done more than this many days ago. Team-managed boards "
            "default to 14 like Jira. 0 shows all.",
        ),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", help="Maximum issues to load.")] = 200,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Show a board as columns of issues, like the Jira board view."""
    config = load_config()

    async def _run() -> tuple[dict[str, Any], bool]:
        async with jira_client(config) as client:
            resolved = await _resolve_board_id(client, board_id, config)
            board, configuration = await asyncio.gather(
                client.get_board(resolved), client.get_board_configuration(resolved)
            )
            sprint_jql, active = await _sprint_jql(client, board, sprint)
            # Kanban boards hide old done issues with a sub-filter. Apply it so the
            # view matches what Jira shows.
            sub_filter = configuration.get("subQuery", {}).get("query")
            issues = await client.list_board_issues(
                resolved,
                jql=_and_jql(
                    sprint_jql,
                    sub_filter,
                    _recent_done_jql(board, done_days),
                    "assignee = currentUser()" if mine else None,
                    jql,
                ),
                fields=BOARD_FIELDS,
                limit=limit,
            )
        result = {
            "board": board,
            "sprints": active,
            "columns": group_by_column(configuration, issues),
        }
        return result, len(issues) >= limit

    result, truncated = run_with_status("Loading board…", _run())
    if truncated:
        err_console.print(
            f"[yellow]![/yellow] Showing the first {limit} issues. Raise --limit for more."
        )
    if emit(result, as_json=as_json, jq=jq):
        return
    title = str(result["board"].get("name", ""))
    if sprint is not None:
        title += f" · sprint {sprint}"
    elif result["sprints"]:
        title += " · " + ", ".join(str(s.get("name", "")) for s in result["sprints"])
    with paged():
        render_board(title, result["columns"], link=lambda key: jira_browse_url(config, key))
