"""`bj ruleset` - Bitbucket branch restrictions (the gh ruleset analog, read-only)."""

from __future__ import annotations

from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.commands._common import resolve_repo
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import bitbucket_authorization
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.ui import console

ruleset_app = typer.Typer(help="Inspect Bitbucket branch restrictions.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
RepoOpt = Annotated[str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


@ruleset_app.command(name="list")
def list_rules(
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List a repository's branch restrictions."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.list_branch_restrictions(ref.workspace, ref.repo_slug)

    rules = run_with_status("Loading branch restrictions…", _run())
    if emit(rules, as_json=as_json, jq=jq):
        return
    if not rules:
        console.print("[dim]No branch restrictions.[/dim]")
    for rule in rules:
        pattern = rule.get("pattern") or rule.get("branch_match_kind", "")
        console.print(f"[cyan]{rule.get('id')}[/cyan] {rule.get('kind', '')} [dim]{pattern}[/dim]")
