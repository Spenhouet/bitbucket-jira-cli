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
from bitbucket_jira_cli.git import RepoRef
from bitbucket_jira_cli.gitauth import git_env
from bitbucket_jira_cli.interaction import confirm
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
    protocol: Annotated[
        str | None, typer.Option("--protocol", help="https or ssh (default: configured).")
    ] = None,
) -> None:
    """Clone a repository locally (HTTPS uses your bj token automatically)."""
    config = load_config()
    ref = resolve_repo(repo)
    proto = (protocol or config.git_protocol).lower()
    if proto not in ("https", "ssh"):
        msg = "--protocol must be 'https' or 'ssh'."
        raise BjError(msg)

    async def _run() -> str:
        async with _bb(config) as client:
            repo_obj = await client.get_repo(ref.workspace, ref.repo_slug)
        return _clone_url(repo_obj, proto)

    url = run_with_status("Loading repository…", _run())
    # HTTPS clones authenticate non-interactively with the stored token; SSH uses
    # the user's keys (token env is harmless there — git won't call askpass).
    env = git_env(config) if proto == "https" else None
    args = ["git", "clone", url]
    if directory:
        args.append(directory)
    result = subprocess.run(args, check=False, env=env)  # noqa: S603
    if result.returncode != 0:
        if proto == "ssh":
            hint = "Ensure your SSH key is registered with Bitbucket, or use --protocol https."
        else:
            hint = "Check `bj auth status` and that the repository exists."
        msg = f"git clone failed. {hint}"
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


YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]


def _new_ref(repo: str, config: Config) -> RepoRef:
    """WORKSPACE/REPO, or REPO with the configured/default workspace."""
    if "/" in repo:
        workspace, slug = repo.split("/", 1)
        return RepoRef(workspace, slug)
    return RepoRef(resolve_workspace(None, config.bitbucket.workspace), repo)


@repo_app.command()
def create(
    repo: Annotated[str, typer.Argument(help="WORKSPACE/REPO (or REPO with a default workspace).")],
    description: Annotated[str | None, typer.Option("--description", "-d")] = None,
    private: Annotated[
        bool, typer.Option("--private/--public", help="Repository visibility.")
    ] = True,
    project: Annotated[
        str | None, typer.Option("--project", help="Project key to create the repo under.")
    ] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Create a new repository (needs a token with repository write scope)."""
    config = load_config()
    ref = _new_ref(repo, config)
    body: dict = {"scm": "git", "is_private": private}
    if description:
        body["description"] = description
    if project:
        body["project"] = {"key": project}

    async def _run() -> dict:
        async with _bb(config) as client:
            return await client.create_repo(ref.workspace, ref.repo_slug, body)

    created = run_with_status("Creating repository…", _run())
    if not emit(created, as_json=as_json, jq=jq):
        success(f"Created {ref}")
        render_repo(created)


@repo_app.command()
def fork(
    repo: Annotated[str, typer.Argument(help="Source WORKSPACE/REPO to fork.")],
    workspace: Annotated[
        str | None, typer.Option("--workspace", help="Destination workspace (default: yours).")
    ] = None,
    name: Annotated[str | None, typer.Option("--name", help="Name for the fork.")] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Fork a repository into a workspace."""
    config = load_config()
    ref = resolve_repo(repo)
    body: dict = {}
    if workspace:
        body["workspace"] = {"slug": workspace}
    if name:
        body["name"] = name

    async def _run() -> dict:
        async with _bb(config) as client:
            return await client.fork_repo(ref.workspace, ref.repo_slug, body)

    forked = run_with_status("Forking…", _run())
    if not emit(forked, as_json=as_json, jq=jq):
        success(f"Forked {ref} to {forked.get('full_name', '?')}")


@repo_app.command()
def delete(
    repo: Annotated[str, typer.Argument(help="WORKSPACE/REPO to delete.")],
    yes: YesOpt = False,
) -> None:
    """Delete a repository (irreversible; needs repository admin scope)."""
    config = load_config()
    ref = _new_ref(repo, config)
    if not confirm(f"Delete {ref}? This cannot be undone.", yes=yes):
        raise typer.Abort

    async def _run() -> None:
        async with _bb(config) as client:
            await client.delete_repo(ref.workspace, ref.repo_slug)

    run_with_status("Deleting…", _run())
    success(f"Deleted {ref}")


@repo_app.command()
def edit(
    repo: Annotated[
        str | None, typer.Argument(help="WORKSPACE/REPO (default: git remote).")
    ] = None,
    description: Annotated[str | None, typer.Option("--description", "-d")] = None,
    private: Annotated[
        bool | None, typer.Option("--private/--public", help="Change visibility.")
    ] = None,
    name: Annotated[str | None, typer.Option("--name", help="Rename the repository.")] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Edit repository settings (description, visibility, name)."""
    config = load_config()
    ref = resolve_repo(repo)
    body: dict = {}
    if description is not None:
        body["description"] = description
    if private is not None:
        body["is_private"] = private
    if name is not None:
        body["name"] = name
    if not body:
        msg = "Nothing to edit. Pass --description, --private/--public, or --name."
        raise BjError(msg)

    async def _run() -> dict:
        async with _bb(config) as client:
            return await client.update_repo(ref.workspace, ref.repo_slug, body)

    updated = run_with_status("Updating…", _run())
    if not emit(updated, as_json=as_json, jq=jq):
        success(f"Updated {ref}")
        render_repo(updated)


@repo_app.command()
def rename(
    new_name: Annotated[str, typer.Argument(help="New repository name.")],
    repo: Annotated[
        str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO (default: git remote).")
    ] = None,
) -> None:
    """Rename a repository."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> dict:
        async with _bb(config) as client:
            return await client.update_repo(ref.workspace, ref.repo_slug, {"name": new_name})

    run_with_status("Renaming…", _run())
    success(f"Renamed {ref} to '{new_name}'")


@repo_app.command()
def file(
    path: Annotated[str, typer.Argument(help="File path in the repository.")],
    ref: Annotated[str, typer.Option("--ref", help="Branch, tag, or commit.")] = "HEAD",
    repo: Annotated[
        str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO (default: git remote).")
    ] = None,
) -> None:
    """Print the contents of a file in the repository."""
    config = load_config()
    repo_ref = resolve_repo(repo)
    real_ref = _resolve_ref(config, repo_ref, ref)

    async def _run() -> str:
        async with _bb(config) as client:
            return await client.get_source(repo_ref.workspace, repo_ref.repo_slug, real_ref, path)

    console.print(run_with_status("Loading file…", _run()), highlight=False, markup=False)


@repo_app.command(name="ls")
def list_dir(
    path: Annotated[str, typer.Argument(help="Directory path (default: root).")] = "",
    ref: Annotated[str, typer.Option("--ref", help="Branch, tag, or commit.")] = "HEAD",
    repo: Annotated[
        str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO (default: git remote).")
    ] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List files in a repository directory."""
    config = load_config()
    repo_ref = resolve_repo(repo)
    real_ref = _resolve_ref(config, repo_ref, ref)

    async def _run() -> list[dict]:
        async with _bb(config) as client:
            return await client.list_source(repo_ref.workspace, repo_ref.repo_slug, real_ref, path)

    entries = run_with_status("Listing…", _run())
    if not emit(entries, as_json=as_json, jq=jq):
        for entry in entries:
            mark = "d" if entry.get("type") == "commit_directory" else "-"
            console.print(f"{mark} {entry.get('path', '')}")


def _resolve_ref(config: Config, repo_ref: RepoRef, ref: str) -> str:
    """Turn 'HEAD' into the repo's main branch; pass anything else through."""
    if ref != "HEAD":
        return ref

    async def _run() -> str:
        async with _bb(config) as client:
            repo_obj = await client.get_repo(repo_ref.workspace, repo_ref.repo_slug)
        return repo_obj.get("mainbranch", {}).get("name", "master")

    return run_with_status("Resolving default branch…", _run())


deploy_key_app = typer.Typer(help="Manage repository access/deploy keys.", no_args_is_help=True)
repo_app.add_typer(deploy_key_app, name="deploy-key")


@deploy_key_app.command(name="list")
def list_deploy_keys(
    repo: Annotated[
        str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO (default: git remote).")
    ] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List a repository's access keys."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> list[dict]:
        async with _bb(config) as client:
            return await client.list_deploy_keys(ref.workspace, ref.repo_slug)

    keys = run_with_status("Loading keys…", _run())
    if not emit(keys, as_json=as_json, jq=jq):
        if not keys:
            console.print("[dim]No access keys.[/dim]")
        for key in keys:
            snippet = str(key.get("key", ""))[:40]
            console.print(
                f"[cyan]{key.get('id')}[/cyan] {key.get('label', '')} [dim]{snippet}…[/dim]"
            )


@deploy_key_app.command(name="add")
def add_deploy_key(
    key_file: Annotated[str, typer.Argument(help="Path to the public key file.")],
    title: Annotated[str, typer.Option("--title", "-t", help="Label for the key.")],
    repo: Annotated[
        str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO (default: git remote).")
    ] = None,
) -> None:
    """Add an access key to a repository."""
    config = load_config()
    ref = resolve_repo(repo)
    key_text = Path(key_file).read_text(encoding="utf-8").strip()

    async def _run() -> dict:
        async with _bb(config) as client:
            return await client.add_deploy_key(ref.workspace, ref.repo_slug, key_text, title)

    created = run_with_status("Adding key…", _run())
    success(f"Added access key #{created.get('id')} ({title})")


@deploy_key_app.command(name="delete")
def delete_deploy_key(
    key_id: Annotated[int, typer.Argument(help="Key id (from `deploy-key list`).")],
    repo: Annotated[
        str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO (default: git remote).")
    ] = None,
    yes: YesOpt = False,
) -> None:
    """Delete a repository access key."""
    config = load_config()
    ref = resolve_repo(repo)
    if not confirm(f"Delete access key #{key_id}?", yes=yes):
        raise typer.Abort

    async def _run() -> None:
        async with _bb(config) as client:
            await client.delete_deploy_key(ref.workspace, ref.repo_slug, key_id)

    run_with_status("Deleting…", _run())
    success(f"Deleted access key #{key_id}")
