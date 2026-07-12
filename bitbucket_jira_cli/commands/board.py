"""`bj board` - Jira Software boards and sprints (the gh project analog)."""

from __future__ import annotations

from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.ui import console

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
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List a board's sprints."""
    config = load_config()

    async def _run() -> list[dict[str, Any]]:
        async with jira_client(config) as client:
            return await client.list_sprints(board_id)

    sprint_list = run_with_status("Loading sprints…", _run())
    if emit(sprint_list, as_json=as_json, jq=jq):
        return
    if not sprint_list:
        console.print("[dim]No sprints.[/dim]")
    for sprint in sprint_list:
        state = sprint.get("state", "")
        name = sprint.get("name", "")
        console.print(f"[cyan]{sprint.get('id')}[/cyan] {name} [dim]{state}[/dim]")
