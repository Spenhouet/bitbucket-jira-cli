"""`bj repo` — Bitbucket repositories (view, list, clone, set-default)."""

from __future__ import annotations

import subprocess
import webbrowser
from pathlib import Path
from typing import Annotated

import typer

from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.commands._common import resolve_repo
from bitbucket_jira_cli.commands._common import resolve_workspace
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.config import save_config
from bitbucket_jira_cli.context import bitbucket_authorization
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.render import render_repo
from bitbucket_jira_cli.render import render_repo_list
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

repo_app = typer.Typer(help="Work with Bitbucket repositories.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


def _clone_url(repo: dict, protocol: str) -> str:
    for link in repo.get("links", {}).get("clone", []):
        if link.get("name") == protocol:
            return str(link.get("href"))
    msg = f"No {protocol} clone URL on the repository object."
    raise BjError(msg)


@repo_app.command()
def view(
    repo: Annotated[
        str | None, typer.Argument(help="WORKSPACE/REPO (default: git remote).")
    ] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
    web: Annotated[bool, typer.Option("--web", "-w", help="Open in the browser.")] = False,
) -> None:
    """View a repository."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> dict:
        async with _bb(config) as client:
            return await client.get_repo(ref.workspace, ref.repo_slug)

    repo_obj = run_with_status("Loading repository…", _run())
    if web:
        webbrowser.open(repo_obj.get("links", {}).get("html", {}).get("href", ""))
        return
    if not emit(repo_obj, as_json=as_json, jq=jq):
        render_repo(repo_obj)


@repo_app.command(name="list")
def list_repos(
    workspace: Annotated[
        str | None, typer.Argument(help="Workspace (default: configured).")
    ] = None,
    role: Annotated[
        str | None, typer.Option("--role", help="owner|admin|contributor|member.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", help="Max results.")] = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List repositories in a workspace."""
    config = load_config()
    ws = resolve_workspace(workspace, config.bitbucket.workspace)

    async def _run() -> list[dict]:
        async with _bb(config) as client:
            return await client.list_repos(ws, role=role, limit=limit)

    repos = run_with_status("Loading repositories…", _run())
    if not emit(repos, as_json=as_json, jq=jq):
        render_repo_list(repos)


@repo_app.command()
def clone(
    repo: Annotated[str, typer.Argument(help="WORKSPACE/REPO to clone.")],
    directory: Annotated[str | None, typer.Argument(help="Target directory.")] = None,
) -> None:
    """Clone a repository locally."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> str:
        async with _bb(config) as client:
            repo_obj = await client.get_repo(ref.workspace, ref.repo_slug)
        return _clone_url(repo_obj, config.git_protocol)

    url = run_with_status("Loading repository…", _run())
    args = ["git", "clone", url]
    if directory:
        args.append(directory)
    result = subprocess.run(args, check=False)  # noqa: S603
    if result.returncode != 0:
        msg = "git clone failed."
        raise BjError(msg)
    success(f"Cloned {ref} into {directory or Path(ref.repo_slug).name}")


@repo_app.command(name="set-default")
def set_default(
    repo: Annotated[str, typer.Argument(help="WORKSPACE/REPO to treat as default.")],
) -> None:
    """Store the default workspace used when not inside a clone."""
    config = load_config()
    ref = resolve_repo(repo)
    config.bitbucket.workspace = ref.workspace
    save_config(config)
    console.print(f"Default workspace set to [cyan]{ref.workspace}[/cyan].")
