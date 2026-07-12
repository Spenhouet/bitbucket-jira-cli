"""`bj search` - search Bitbucket repositories/code and Jira issues."""

from __future__ import annotations

from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.commands._common import resolve_workspace
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import bitbucket_authorization
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.render import render_issue_list
from bitbucket_jira_cli.render import render_repo_list
from bitbucket_jira_cli.ui import console

search_app = typer.Typer(help="Search Bitbucket and Jira.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
WsOpt = Annotated[
    str | None, typer.Option("--workspace", "-w", help="Workspace (default: configured).")
]
LimitOpt = Annotated[int, typer.Option("--limit", "-L", help="Max results.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


@search_app.command()
def repos(
    query: Annotated[str, typer.Argument(help="Text to match in repository names.")],
    workspace: WsOpt = None,
    limit: LimitOpt = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search repositories in a workspace by name."""
    config = load_config()
    ws = resolve_workspace(workspace, config.bitbucket.workspace)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.list_repos(ws, query=f'name~"{query}"', limit=limit)

    results = run_with_status("Searching…", _run())
    if not emit(results, as_json=as_json, jq=jq):
        render_repo_list(results)


@search_app.command()
def code(
    query: Annotated[str, typer.Argument(help="Code search query.")],
    workspace: WsOpt = None,
    limit: LimitOpt = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search code across a workspace."""
    config = load_config()
    ws = resolve_workspace(workspace, config.bitbucket.workspace)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.search_code(ws, query, limit=limit)

    results = run_with_status("Searching code…", _run())
    if emit(results, as_json=as_json, jq=jq):
        return
    if not results:
        console.print("[dim]No matches.[/dim]")
    for hit in results:
        file_info = hit.get("file", {})
        repo = file_info.get("commit", {}).get("repository", {}).get("full_name", "")
        console.print(f"[cyan]{repo}[/cyan] {file_info.get('path', '')}")


@search_app.command()
def issues(
    jql: Annotated[str, typer.Argument(help="JQL query.")],
    limit: LimitOpt = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search Jira issues with JQL."""
    config = load_config()

    async def _run() -> list[dict[str, Any]]:
        async with jira_client(config) as client:
            return await client.search(jql, limit=limit)

    results = run_with_status("Searching issues…", _run())
    if not emit(results, as_json=as_json, jq=jq):
        render_issue_list(results)
