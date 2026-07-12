"""`bj ssh-key` - manage your Bitbucket account SSH keys.

Needs a token with account write scope for add/delete; listing needs account read.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import bitbucket_authorization
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

sshkey_app = typer.Typer(help="Manage your Bitbucket account SSH keys.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


@sshkey_app.command(name="list")
def list_keys(
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List your account SSH keys."""
    config = load_config()

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            user = await client.current_user()
            return await client.list_ssh_keys(str(user["uuid"]))

    keys = run_with_status("Loading SSH keys…", _run())
    if emit(keys, as_json=as_json, jq=jq):
        return
    if not keys:
        console.print("[dim]No SSH keys.[/dim]")
    for key in keys:
        snippet = str(key.get("key", ""))[:40]
        console.print(
            f"[cyan]{key.get('uuid')}[/cyan] {key.get('label', '')} [dim]{snippet}…[/dim]"
        )


@sshkey_app.command(name="add")
def add_key(
    key_file: Annotated[str, typer.Argument(help="Path to the public key file.")],
    title: Annotated[str, typer.Option("--title", "-t", help="Label for the key.")],
) -> None:
    """Add an SSH key to your account."""
    config = load_config()
    key_text = Path(key_file).read_text(encoding="utf-8").strip()

    async def _run() -> dict[str, Any]:
        async with _bb(config) as client:
            user = await client.current_user()
            return await client.add_ssh_key(str(user["uuid"]), key_text, title)

    created = run_with_status("Adding key…", _run())
    success(f"Added SSH key {created.get('uuid')} ({title})")


@sshkey_app.command(name="delete")
def delete_key(
    key_uuid: Annotated[str, typer.Argument(help="Key uuid (from `ssh-key list`).")],
    yes: YesOpt = False,
) -> None:
    """Delete an SSH key from your account."""
    config = load_config()
    if not confirm(f"Delete SSH key {key_uuid}?", yes=yes):
        raise typer.Abort

    async def _run() -> None:
        async with _bb(config) as client:
            user = await client.current_user()
            await client.delete_ssh_key(str(user["uuid"]), key_uuid)

    run_with_status("Deleting…", _run())
    success(f"Deleted SSH key {key_uuid}")
