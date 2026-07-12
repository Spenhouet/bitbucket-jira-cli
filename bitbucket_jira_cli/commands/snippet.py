"""`bj snippet` - Bitbucket snippets (the gh gist analog)."""

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
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

snippet_app = typer.Typer(help="Work with Bitbucket snippets.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
WsOpt = Annotated[
    str | None, typer.Option("--workspace", "-w", help="Workspace (default: configured).")
]
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


@snippet_app.command(name="list")
def list_snippets(
    workspace: WsOpt = None,
    limit: Annotated[int, typer.Option("--limit", "-L", help="Max results.")] = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List snippets in a workspace."""
    config = load_config()
    ws = resolve_workspace(workspace, config.bitbucket.workspace)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.list_snippets(ws, limit=limit)

    snippets = run_with_status("Loading snippets…", _run())
    if emit(snippets, as_json=as_json, jq=jq):
        return
    if not snippets:
        console.print("[dim]No snippets.[/dim]")
    for snippet in snippets:
        visibility = "private" if snippet.get("is_private") else "public"
        title = snippet.get("title", "")
        console.print(f"[cyan]{snippet.get('id')}[/cyan] {title} [dim]{visibility}[/dim]")


@snippet_app.command()
def view(
    snippet_id: Annotated[str, typer.Argument(help="Snippet id.")],
    workspace: WsOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """View a snippet's metadata and files."""
    config = load_config()
    ws = resolve_workspace(workspace, config.bitbucket.workspace)

    async def _run() -> dict[str, Any]:
        async with _bb(config) as client:
            return await client.get_snippet(ws, snippet_id)

    snippet = run_with_status("Loading snippet…", _run())
    if emit(snippet, as_json=as_json, jq=jq):
        return
    console.print(f"[bold]{snippet.get('title', '')}[/bold] [dim]{snippet.get('id')}[/dim]")
    for name in snippet.get("files", {}):
        console.print(f"  {name}")


@snippet_app.command()
def delete(
    snippet_id: Annotated[str, typer.Argument(help="Snippet id.")],
    workspace: WsOpt = None,
    yes: YesOpt = False,
) -> None:
    """Delete a snippet."""
    config = load_config()
    ws = resolve_workspace(workspace, config.bitbucket.workspace)
    if not confirm(f"Delete snippet {snippet_id}?", yes=yes):
        raise typer.Abort

    async def _run() -> None:
        async with _bb(config) as client:
            await client.delete_snippet(ws, snippet_id)

    run_with_status("Deleting…", _run())
    success(f"Deleted snippet {snippet_id}")
