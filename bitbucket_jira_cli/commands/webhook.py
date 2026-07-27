"""`bj webhook` - Bitbucket webhooks.

Bitbucket registers webhooks on one of two subject types: a single repository or a
whole workspace. Both are covered here: commands default to the current repository,
and `--workspace NAME` switches to workspace scope.

There is no `forward` subcommand (the `gh webhook` extension's only command).
Forwarding relies on a GitHub-side relay service; Bitbucket has no equivalent.
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
from bitbucket_jira_cli.errors import ApiError
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

webhook_app = typer.Typer(help="Manage Bitbucket webhooks.", no_args_is_help=True)

BAD_REQUEST = 400

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
RepoOpt = Annotated[str | None, typer.Option("--repo", "-R", help="WORKSPACE/REPO.")]
WsOpt = Annotated[
    str | None,
    typer.Option("--workspace", "-W", help="Operate on a workspace's webhooks instead."),
]
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


def _target(repo: str | None, workspace: str | None) -> tuple[str, str | None]:
    """Resolve the webhook subject: (workspace, repo_slug) with repo_slug None for a workspace."""
    if workspace:
        if repo:
            msg = "Pass either --repo or --workspace, not both."
            raise BjError(msg)
        return workspace, None
    ref = resolve_repo(repo)
    return ref.workspace, ref.repo_slug


def _scope_label(workspace: str, repo_slug: str | None) -> str:
    return f"{workspace}/{repo_slug}" if repo_slug else workspace


async def _explain_bad_events(
    client: BitbucketClient, events: list[str], repo_slug: str | None, error: ApiError
) -> None:
    """Turn a 400 into a useful message when an event name is not a real Bitbucket event.

    Bitbucket answers an unknown event with a bare "Bad request", so check the names
    against the catalog and say which ones are wrong. Always raises.
    """
    subject = "repository" if repo_slug else "workspace"
    try:
        catalog = await client.list_hook_events(subject)
    except ApiError:
        raise error from None
    known = {str(entry.get("event")) for entry in catalog}
    unknown = [name for name in events if name not in known]
    if not unknown:
        raise error
    msg = (
        f"Unknown {subject} webhook event: {', '.join(unknown)}. "
        f"Run `bj webhook events --subject {subject}` for the valid names."
    )
    raise BjError(msg) from None


def _render(hook: dict[str, Any]) -> None:
    state = "[green]active[/green]" if hook.get("active") else "[dim]inactive[/dim]"
    secret = " [dim]secret set[/dim]" if hook.get("secret_set") else ""
    console.print(f"[cyan]{hook.get('uuid')}[/cyan] {hook.get('url', '')} {state}{secret}")
    description = hook.get("description")
    if description and description != hook.get("url"):
        console.print(f"  [dim]{description}[/dim]")
    events = hook.get("events") or []
    if events:
        console.print(f"  [dim]{', '.join(events)}[/dim]")


@webhook_app.command(name="list")
def list_webhooks(
    repo: RepoOpt = None,
    workspace: WsOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List webhooks on a repository or workspace."""
    config = load_config()
    ws, slug = _target(repo, workspace)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.list_webhooks(ws, slug)

    hooks = run_with_status("Loading webhooks…", _run())
    if emit(hooks, as_json=as_json, jq=jq):
        return
    if not hooks:
        console.print(f"[dim]No webhooks on {_scope_label(ws, slug)}.[/dim]")
    for hook in hooks:
        _render(hook)


@webhook_app.command()
def view(
    uid: Annotated[str, typer.Argument(help="Webhook uuid (from `webhook list`).")],
    repo: RepoOpt = None,
    workspace: WsOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """View a single webhook."""
    config = load_config()
    ws, slug = _target(repo, workspace)

    async def _run() -> dict[str, Any]:
        async with _bb(config) as client:
            return await client.get_webhook(ws, uid, slug)

    hook = run_with_status("Loading webhook…", _run())
    if emit(hook, as_json=as_json, jq=jq):
        return
    _render(hook)


@webhook_app.command()
def create(
    url: Annotated[str, typer.Option("--url", "-u", help="Payload URL to POST events to.")],
    event: Annotated[
        list[str] | None,
        typer.Option("--event", "-e", help="Event to subscribe to; repeat for several."),
    ] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="Label (default: the URL).")
    ] = None,
    secret: Annotated[
        str | None, typer.Option("--secret", help="Shared secret used to sign payloads.")
    ] = None,
    inactive: Annotated[
        bool, typer.Option("--inactive", help="Create it disabled.")
    ] = False,
    repo: RepoOpt = None,
    workspace: WsOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Create a webhook. See `bj webhook events` for the event names."""
    config = load_config()
    ws, slug = _target(repo, workspace)
    events = event or ["repo:push"]

    async def _run() -> dict[str, Any]:
        async with _bb(config) as client:
            try:
                return await client.create_webhook(
                    ws,
                    url,
                    events,
                    repo_slug=slug,
                    description=description,
                    active=not inactive,
                    secret=secret,
                )
            except ApiError as exc:
                if exc.status != BAD_REQUEST:
                    raise
                await _explain_bad_events(client, events, slug, exc)
                raise  # unreachable; _explain_bad_events always raises

    hook = run_with_status("Creating webhook…", _run())
    if emit(hook, as_json=as_json, jq=jq):
        return
    success(f"Created webhook {hook.get('uuid')} on {_scope_label(ws, slug)}")
    _render(hook)


@webhook_app.command()
def edit(
    uid: Annotated[str, typer.Argument(help="Webhook uuid.")],
    url: Annotated[str | None, typer.Option("--url", "-u", help="New payload URL.")] = None,
    event: Annotated[
        list[str] | None,
        typer.Option("--event", "-e", help="Replace the event list; repeat for several."),
    ] = None,
    description: Annotated[
        str | None, typer.Option("--description", "-d", help="New label.")
    ] = None,
    secret: Annotated[str | None, typer.Option("--secret", help="Replace the secret.")] = None,
    active: Annotated[
        bool | None,
        typer.Option("--active/--inactive", help="Enable or disable the webhook."),
    ] = None,
    repo: RepoOpt = None,
    workspace: WsOpt = None,
) -> None:
    """Edit a webhook. Only the fields you pass change."""
    config = load_config()
    ws, slug = _target(repo, workspace)
    if url is None and not event and description is None and secret is None and active is None:
        msg = "Nothing to change. Pass at least one of --url, --event, --description, --secret, --active/--inactive."  # noqa: E501
        raise BjError(msg)

    async def _run() -> dict[str, Any]:
        async with _bb(config) as client:
            # Bitbucket's PUT replaces the subscription, so merge onto the current one.
            current = await client.get_webhook(ws, uid, slug)
            body: dict[str, Any] = {
                "url": url if url is not None else current.get("url"),
                "events": event or current.get("events", []),
                "description": (
                    description if description is not None else current.get("description")
                ),
                "active": active if active is not None else bool(current.get("active")),
            }
            if secret:
                body["secret"] = secret
            try:
                return await client.update_webhook(ws, uid, body, slug)
            except ApiError as exc:
                if exc.status != BAD_REQUEST:
                    raise
                await _explain_bad_events(client, list(body["events"]), slug, exc)
                raise  # unreachable; _explain_bad_events always raises

    hook = run_with_status("Updating webhook…", _run())
    success(f"Updated webhook {hook.get('uuid')}")
    _render(hook)


@webhook_app.command()
def delete(
    uid: Annotated[str, typer.Argument(help="Webhook uuid.")],
    repo: RepoOpt = None,
    workspace: WsOpt = None,
    yes: YesOpt = False,
) -> None:
    """Delete a webhook."""
    config = load_config()
    ws, slug = _target(repo, workspace)
    if not confirm(f"Delete webhook {uid} on {_scope_label(ws, slug)}?", yes=yes):
        raise typer.Abort

    async def _run() -> None:
        async with _bb(config) as client:
            await client.delete_webhook(ws, uid, slug)

    run_with_status("Deleting…", _run())
    success(f"Deleted webhook {uid}")


@webhook_app.command()
def events(
    subject: Annotated[
        str, typer.Option("--subject", "-s", help="Subject type: repository or workspace.")
    ] = "repository",
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List the events a webhook can subscribe to."""
    config = load_config()

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.list_hook_events(subject)

    catalog = run_with_status("Loading events…", _run())
    if emit(catalog, as_json=as_json, jq=jq):
        return
    for entry in catalog:
        label = entry.get("label", "")
        console.print(f"[cyan]{entry.get('event')}[/cyan] [dim]{label}[/dim]")
