"""Cross-cutting commands: `bj browse` and `bj api`."""

from __future__ import annotations

import webbrowser
from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli._async import run

# Backend is a Literal used in a Typer signature, so it must stay a runtime
# import (Typer resolves annotations at runtime); TC001 is a false positive.
from bitbucket_jira_cli.auth.store import Backend  # noqa: TC001
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.commands._common import resolve_repo
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import bitbucket_authorization
from bitbucket_jira_cli.context import bitbucket_client
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.git import current_branch
from bitbucket_jira_cli.git import parse_branch_key
from bitbucket_jira_cli.ui import console


def _emit_url(url: str, *, no_browser: bool) -> None:
    if no_browser:
        console.print(url)
        return
    webbrowser.open(url)
    console.print(f"[dim]Opening {url}[/dim]")


async def _current_branch_pr_url(config: Config, workspace: str, repo_slug: str) -> str:
    branch = current_branch()
    if not branch:
        msg = "Not on a git branch; cannot resolve the current PR."
        raise BjError(msg)
    client = bitbucket_client(config)
    async with client:
        prs = await client.list_prs(workspace, repo_slug, source_branch=branch, limit=1)
    if not prs:
        msg = f"No open PR for branch '{branch}'."
        raise BjError(msg)
    return str(prs[0].get("links", {}).get("html", {}).get("href", ""))


def browse(
    target: Annotated[
        str | None, typer.Argument(help="'pr', 'issue', or omit for the repo home.")
    ] = None,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", "-n", help="Print the URL only.")
    ] = False,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO.")] = None,
) -> None:
    """Open the repository, current PR, or branch's Jira issue in the browser."""
    config = load_config()
    if target == "issue":
        key = parse_branch_key(current_branch() or "", config.branch_key)
        if not key or not config.jira.site:
            msg = "No Jira key in the branch, or Jira site not configured."
            raise BjError(msg)
        _emit_url(f"{config.jira.site}/browse/{key}", no_browser=no_browser)
        return
    ref = resolve_repo(repo)
    if target == "pr":
        url = run(_current_branch_pr_url(config, ref.workspace, ref.repo_slug))
        _emit_url(url, no_browser=no_browser)
        return
    _emit_url(f"https://bitbucket.org/{ref}", no_browser=no_browser)


def api(
    path: Annotated[str, typer.Argument(help="API path, e.g. /repositories/{ws}/{repo}.")],
    backend: Annotated[
        Backend, typer.Option("--backend", "-b", help="Which API to call.")
    ] = "bitbucket",
    method: Annotated[str, typer.Option("--method", "-X", help="HTTP method.")] = "GET",
    field: Annotated[
        list[str] | None, typer.Option("--field", "-f", help="key=value parameter (repeatable).")
    ] = None,
    jq: Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with jq.")] = None,
) -> None:
    """Make an authenticated request to the Bitbucket or Jira API."""
    config = load_config()
    fields: dict[str, str] = {}
    for item in field or []:
        if "=" not in item:
            msg = f"--field must be key=value, got '{item}'."
            raise BjError(msg)
        k, v = item.split("=", 1)
        fields[k] = v
    upper = method.upper()
    params = fields if upper == "GET" and fields else None
    json_body: dict[str, Any] | None = fields if upper != "GET" and fields else None

    async def _run() -> None:
        client = jira_client(config) if backend == "jira" else bitbucket_client(config)
        async with client:
            data = await client.raw(upper, path, params=params, json=json_body)
        emit(data, as_json=not jq, jq=jq)

    # Ensure bitbucket_authorization errors surface early with a clean message.
    if backend == "bitbucket":
        bitbucket_authorization(config)
    run(_run())
