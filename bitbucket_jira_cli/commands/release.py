"""`bj release` - Jira project versions (the gh release analog).

GitHub releases map to Jira versions: a named milestone on a project that issues
target via their fix version, and that you eventually mark released.
"""

from __future__ import annotations

from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

release_app = typer.Typer(help="Manage Jira project versions (releases).", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]


def _render_versions(versions: list[dict[str, Any]]) -> None:
    if not versions:
        console.print("[dim]No versions.[/dim]")
        return
    for version in versions:
        state = "[green]released[/green]" if version.get("released") else "[yellow]unreleased[/yellow]"  # noqa: E501
        date = version.get("releaseDate", "")
        date_suffix = f" [dim]{date}[/dim]" if date else ""
        name = version.get("name")
        console.print(f"[cyan]{version.get('id')}[/cyan] {name} · {state}{date_suffix}")


@release_app.command(name="list")
def list_versions(
    project: Annotated[str, typer.Option("--project", "-p", help="Project key.")],
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List a project's versions."""
    config = load_config()

    async def _run() -> list[dict[str, Any]]:
        async with jira_client(config) as client:
            return await client.list_versions(project)

    versions = run_with_status("Loading versions…", _run())
    if not emit(versions, as_json=as_json, jq=jq):
        _render_versions(versions)


@release_app.command()
def view(
    version_id: Annotated[str, typer.Argument(help="Version id.")],
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """View a single version."""
    config = load_config()

    async def _run() -> dict[str, Any]:
        async with jira_client(config) as client:
            return await client.get_version(version_id)

    version = run_with_status("Loading version…", _run())
    if not emit(version, as_json=as_json, jq=jq):
        _render_versions([version])


@release_app.command()
def create(
    name: Annotated[str, typer.Argument(help="Version name, e.g. '1.2.0'.")],
    project: Annotated[str, typer.Option("--project", "-p", help="Project key.")],
    description: Annotated[str | None, typer.Option("--description", "-d")] = None,
    release_date: Annotated[
        str | None, typer.Option("--release-date", help="YYYY-MM-DD.")
    ] = None,
    released: Annotated[bool, typer.Option("--released", help="Create already released.")] = False,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Create a version on a project."""
    config = load_config()

    async def _run() -> dict[str, Any]:
        async with jira_client(config) as client:
            project_id = int((await client.get_project(project))["id"])
            body: dict[str, Any] = {"name": name, "projectId": project_id, "released": released}
            if description:
                body["description"] = description
            if release_date:
                body["releaseDate"] = release_date
            return await client.create_version(body)

    created = run_with_status("Creating version…", _run())
    if not emit(created, as_json=as_json, jq=jq):
        success(f"Created version {created.get('name')} ({created.get('id')})")


@release_app.command()
def edit(
    version_id: Annotated[str, typer.Argument(help="Version id.")],
    name: Annotated[str | None, typer.Option("--name")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d")] = None,
    release_date: Annotated[str | None, typer.Option("--release-date", help="YYYY-MM-DD.")] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Edit a version's fields."""
    config = load_config()
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if release_date is not None:
        body["releaseDate"] = release_date
    if not body:
        msg = "Nothing to edit. Pass --name, --description, or --release-date."
        raise BjError(msg)

    async def _run() -> dict[str, Any]:
        async with jira_client(config) as client:
            return await client.update_version(version_id, body)

    updated = run_with_status("Updating…", _run())
    if not emit(updated, as_json=as_json, jq=jq):
        success(f"Updated version {updated.get('name')}")


@release_app.command()
def release(
    version_id: Annotated[str, typer.Argument(help="Version id.")],
    release_date: Annotated[str | None, typer.Option("--release-date", help="YYYY-MM-DD.")] = None,
) -> None:
    """Mark a version as released."""
    config = load_config()
    body: dict[str, Any] = {"released": True}
    if release_date:
        body["releaseDate"] = release_date

    async def _run() -> dict[str, Any]:
        async with jira_client(config) as client:
            return await client.update_version(version_id, body)

    updated = run_with_status("Releasing…", _run())
    success(f"Released version {updated.get('name')}")


@release_app.command()
def unrelease(
    version_id: Annotated[str, typer.Argument(help="Version id.")],
) -> None:
    """Mark a version as unreleased."""
    config = load_config()

    async def _run() -> dict[str, Any]:
        async with jira_client(config) as client:
            return await client.update_version(version_id, {"released": False})

    updated = run_with_status("Updating…", _run())
    success(f"Unreleased version {updated.get('name')}")


@release_app.command()
def delete(
    version_id: Annotated[str, typer.Argument(help="Version id.")],
    yes: YesOpt = False,
) -> None:
    """Delete a version."""
    config = load_config()
    if not confirm(f"Delete version {version_id}?", yes=yes):
        raise typer.Abort

    async def _run() -> None:
        async with jira_client(config) as client:
            await client.delete_version(version_id)

    run_with_status("Deleting…", _run())
    success(f"Deleted version {version_id}")
