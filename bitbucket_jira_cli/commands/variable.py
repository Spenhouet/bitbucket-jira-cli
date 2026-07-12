"""`bj variable` - Bitbucket Pipelines variables (the gh variable/secret analog).

Bitbucket models both plaintext variables and secrets as one resource: a pipeline
variable with a `secured` flag. So `--secured` covers what `gh secret` does.
"""

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
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

variable_app = typer.Typer(
    help="Manage Bitbucket Pipelines variables (use --secured for secrets).",
    no_args_is_help=True,
)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
RepoOpt = Annotated[str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


@variable_app.command(name="list")
def list_variables(
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List a repository's pipeline variables."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.list_pipeline_variables(ref.workspace, ref.repo_slug)

    variables = run_with_status("Loading variables…", _run())
    if emit(variables, as_json=as_json, jq=jq):
        return
    if not variables:
        console.print("[dim]No variables.[/dim]")
    for var in variables:
        value = "[dim](secured)[/dim]" if var.get("secured") else var.get("value", "")
        console.print(f"[cyan]{var.get('key')}[/cyan] = {value}")


@variable_app.command(name="set")
def set_variable(
    key: Annotated[str, typer.Argument(help="Variable name.")],
    value: Annotated[str, typer.Argument(help="Variable value.")],
    secured: Annotated[
        bool, typer.Option("--secured", help="Store as a secret (write-only).")
    ] = False,
    repo: RepoOpt = None,
) -> None:
    """Set a pipeline variable (creates or replaces it)."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> None:
        async with _bb(config) as client:
            existing = await client.list_pipeline_variables(ref.workspace, ref.repo_slug)
            for var in existing:
                if var.get("key") == key:
                    await client.delete_pipeline_variable(
                        ref.workspace, ref.repo_slug, str(var.get("uuid"))
                    )
                    break
            await client.create_pipeline_variable(
                ref.workspace, ref.repo_slug, key, value, secured=secured
            )

    run_with_status("Setting variable…", _run())
    success(f"Set variable {key}")


@variable_app.command(name="delete")
def delete_variable(
    key: Annotated[str, typer.Argument(help="Variable name.")],
    repo: RepoOpt = None,
) -> None:
    """Delete a pipeline variable by name."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> None:
        async with _bb(config) as client:
            existing = await client.list_pipeline_variables(ref.workspace, ref.repo_slug)
            for var in existing:
                if var.get("key") == key:
                    await client.delete_pipeline_variable(
                        ref.workspace, ref.repo_slug, str(var.get("uuid"))
                    )
                    return
            msg = f"No variable named '{key}'."
            raise BjError(msg)

    run_with_status("Deleting variable…", _run())
    success(f"Deleted variable {key}")
