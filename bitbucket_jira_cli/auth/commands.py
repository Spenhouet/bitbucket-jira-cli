"""`bj auth` — login, status, logout, token. Validates against both backends."""

from __future__ import annotations

import sys
from typing import Annotated
from typing import Any

import questionary
import typer

from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.api.jira import JiraClient
from bitbucket_jira_cli.api.jira import fetch_cloud_id
from bitbucket_jira_cli.auth.store import BACKENDS
from bitbucket_jira_cli.auth.store import Backend
from bitbucket_jira_cli.auth.store import basic_header
from bitbucket_jira_cli.auth.store import delete_token
from bitbucket_jira_cli.auth.store import get_token
from bitbucket_jira_cli.auth.store import set_token
from bitbucket_jira_cli.auth.store import token_source
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.config import save_config
from bitbucket_jira_cli.context import jira_rest_base
from bitbucket_jira_cli.errors import ApiError
from bitbucket_jira_cli.errors import AuthError
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

auth_app = typer.Typer(help="Authenticate bj with Bitbucket and Jira.", no_args_is_help=True)


def _which(bitbucket: bool, jira: bool) -> tuple[bool, bool]:
    """Neither flag → both backends; otherwise only the requested one(s)."""
    if not bitbucket and not jira:
        return True, True
    return bitbucket, jira


async def _validate_bitbucket(authorization: str) -> str:
    async with BitbucketClient(authorization) as client:
        user = await client.current_user()
    return str(user.get("display_name") or user.get("username") or user.get("nickname") or "?")


async def _validate_jira(base_url: str, authorization: str) -> str:
    async with JiraClient(base_url, authorization) as client:
        me = await client.myself()
    return str(me.get("displayName") or me.get("emailAddress") or "?")


ATLASSIAN_ID_URL = "https://id.atlassian.com/manage-profile/security/api-tokens"


def _guide_bitbucket() -> None:
    console.print("[bold]Bitbucket Cloud[/bold]")
    console.print(
        f"[dim]Basic mode — create a scoped API token (app: Bitbucket):\n"
        f"  {ATLASSIAN_ID_URL}\n"
        f"  scopes: read:user:bitbucket, read:workspace:bitbucket, read:repository:bitbucket,\n"
        f"          read:pullrequest:bitbucket, write:pullrequest:bitbucket,\n"
        f"          read:pipeline:bitbucket, write:pipeline:bitbucket\n"
        f"Bearer mode — paste a repository/workspace access token from repo settings.[/dim]",
        highlight=False,
    )


def _guide_jira() -> None:
    console.print("[bold]Jira Cloud[/bold]")
    console.print(
        f"[dim]Create an API token at {ATLASSIAN_ID_URL}\n"
        f"  • Unscoped (simplest): the plain 'Create API token' button — no scopes.\n"
        f"  • Scoped (least privilege): 'Create API token with scopes', app: Jira,\n"
        f"    scopes read:jira-work, write:jira-work, read:jira-user. bj addresses it\n"
        f"    through the api.atlassian.com gateway (cloudId resolved automatically).\n"
        f"  Pick the matching method at the next prompt.[/dim]",
        highlight=False,
    )


def _ask(question: Any) -> str:
    """Run a questionary prompt; abort cleanly on Ctrl-C / EOF (returns None)."""
    answer = question.ask()
    if answer is None:
        raise typer.Abort
    return str(answer).strip()


_BB_MODE_CHOICES = [
    questionary.Choice("API token (Atlassian account) — recommended", value="basic"),
    questionary.Choice("Access token (repository / workspace / project)", value="bearer"),
]


def _login_bitbucket(config: Config, *, insecure: bool, token_stdin: str | None) -> None:
    if token_stdin is not None:
        # Non-interactive: reuse the configured mode/email, just store the token.
        console.print("[bold]Bitbucket Cloud[/bold]")
        mode = config.bitbucket.auth_mode
        email = config.bitbucket.email or ""
        if mode == "basic" and not email:
            msg = "Bitbucket --with-token needs bitbucket.email already configured."
            raise AuthError(msg)
        token = token_stdin
    else:
        _guide_bitbucket()
        mode = _ask(
            questionary.select(
                "Authentication method",
                choices=_BB_MODE_CHOICES,
                default=config.bitbucket.auth_mode,
            )
        )
        email = config.bitbucket.email or ""
        if mode == "basic":
            email = _ask(questionary.text("Atlassian account email", default=email))
        label = "API token" if mode == "basic" else "Access token"
        token = _ask(questionary.password(label))

    authorization = f"Bearer {token}" if mode == "bearer" else basic_header(email, token)
    try:
        name = run(_validate_bitbucket(authorization))
    except ApiError as exc:
        msg = f"Bitbucket rejected the credentials: {exc.message}"
        raise AuthError(msg) from exc
    config.bitbucket.auth_mode = mode
    config.bitbucket.email = email or None
    where = set_token("bitbucket", token, insecure=insecure)
    success(f"Logged in to Bitbucket as {name} (token in {where}).")


_JIRA_MODE_CHOICES = [
    questionary.Choice("Unscoped API token — simplest (your site host)", value="site"),
    questionary.Choice("Scoped API token — least privilege (api.atlassian.com)", value="gateway"),
]


def _jira_base(mode: str, site: str) -> tuple[str, str | None]:
    """Return (rest_base_url, cloud_id) for the chosen mode, resolving cloudId."""
    if mode == "gateway":
        try:
            cloud_id = run(fetch_cloud_id(site))
        except ApiError as exc:
            msg = f"Could not resolve the cloudId for {site}: {exc.message}"
            raise AuthError(msg) from exc
        return f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3", cloud_id
    return site.rstrip("/") + "/rest/api/3", None


def _login_jira(config: Config, *, insecure: bool, token_stdin: str | None) -> None:
    if token_stdin is not None:
        console.print("[bold]Jira Cloud[/bold]")
        site = (config.jira.site or "").rstrip("/")
        email = config.jira.email or ""
        mode = config.jira.auth_mode
        if not (site and email):
            msg = "Jira --with-token needs jira.site and jira.email already configured."
            raise AuthError(msg)
        token = token_stdin
    else:
        _guide_jira()
        mode = _ask(
            questionary.select(
                "Authentication method", choices=_JIRA_MODE_CHOICES, default=config.jira.auth_mode
            )
        )
        site = _ask(
            questionary.text(
                "Site URL (e.g. https://your-domain.atlassian.net)",
                default=config.jira.site or "",
            )
        ).rstrip("/")
        email = _ask(questionary.text("Atlassian account email", default=config.jira.email or ""))
        token = _ask(questionary.password("API token"))

    base, cloud_id = _jira_base(mode, site)
    try:
        name = run(_validate_jira(base, basic_header(email, token)))
    except ApiError as exc:
        msg = f"Jira rejected the credentials: {exc.message}"
        raise AuthError(msg) from exc
    config.jira.site = site
    config.jira.email = email
    config.jira.auth_mode = mode
    config.jira.cloud_id = cloud_id
    where = set_token("jira", token, insecure=insecure)
    success(f"Logged in to Jira as {name} (token in {where}).")


@auth_app.command()
def login(
    bitbucket: Annotated[
        bool, typer.Option("--bitbucket", help="Only configure Bitbucket.")
    ] = False,
    jira: Annotated[bool, typer.Option("--jira", help="Only configure Jira.")] = False,
    insecure_storage: Annotated[
        bool,
        typer.Option(
            "--insecure-storage",
            help="Store tokens in a plaintext file (0600) instead of the OS keyring.",
        ),
    ] = False,
    with_token: Annotated[
        bool,
        typer.Option(
            "--with-token",
            help="Read one token from stdin (requires exactly one of --bitbucket/--jira).",
        ),
    ] = False,
) -> None:
    """Log in to Bitbucket and/or Jira with API tokens (Basic auth)."""
    config = load_config()
    do_bb, do_jira = _which(bitbucket, jira)
    token_stdin: str | None = None
    if with_token:
        if do_bb and do_jira:
            msg = "--with-token requires exactly one of --bitbucket or --jira."
            raise AuthError(msg)
        token_stdin = sys.stdin.read().strip()
    if do_bb:
        _login_bitbucket(config, insecure=insecure_storage, token_stdin=token_stdin)
    if do_jira:
        _login_jira(config, insecure=insecure_storage, token_stdin=token_stdin)
    save_config(config)


def _status_bitbucket(config: Config) -> bool:
    src = token_source("bitbucket")
    if not src:
        console.print("[yellow]-[/yellow] Bitbucket: not logged in")
        return False
    token = get_token("bitbucket") or ""
    authorization = (
        f"Bearer {token}"
        if config.bitbucket.auth_mode == "bearer"
        else basic_header(config.bitbucket.email or "", token)
    )
    try:
        name = run(_validate_bitbucket(authorization))
    except ApiError as exc:
        console.print(f"[red]✗[/red] Bitbucket: token from {src} rejected — {exc.message}")
        return False
    console.print(f"[green]✓[/green] Bitbucket: logged in as [bold]{name}[/bold] ({src})")
    return True


def _status_jira(config: Config) -> bool:
    src = token_source("jira")
    if not (src and config.jira.site and config.jira.email):
        console.print("[yellow]-[/yellow] Jira: not logged in")
        return False
    authorization = basic_header(config.jira.email, get_token("jira") or "")
    try:
        name = run(_validate_jira(jira_rest_base(config), authorization))
    except (ApiError, AuthError) as exc:
        detail = exc.message if isinstance(exc, ApiError) else str(exc)
        console.print(f"[red]✗[/red] Jira: token from {src} rejected — {detail}")
        return False
    mode = "gateway" if config.jira.auth_mode == "gateway" else "site"
    console.print(
        f"[green]✓[/green] Jira: logged in as [bold]{name}[/bold] "
        f"at {config.jira.site} ({mode}, {src})"
    )
    return True


@auth_app.command()
def status() -> None:
    """Show which backends are configured and validate the stored tokens."""
    config = load_config()
    ok_bb = _status_bitbucket(config)
    ok_jira = _status_jira(config)
    if not (ok_bb or ok_jira):
        raise typer.Exit(1)


@auth_app.command()
def logout(
    bitbucket: Annotated[bool, typer.Option("--bitbucket")] = False,
    jira: Annotated[bool, typer.Option("--jira")] = False,
) -> None:
    """Remove stored credentials for one or both backends."""
    do_bb, do_jira = _which(bitbucket, jira)
    if do_bb:
        delete_token("bitbucket")
        success("Logged out of Bitbucket.")
    if do_jira:
        delete_token("jira")
        success("Logged out of Jira.")


@auth_app.command()
def token(
    backend: Annotated[Backend, typer.Argument(help="Which backend's token to print.")],
) -> None:
    """Print the stored token for a backend (for scripting)."""
    if backend not in BACKENDS:
        msg = f"Unknown backend '{backend}'."
        raise AuthError(msg)
    value = get_token(backend)
    if not value:
        raise typer.Exit(1)
    sys.stdout.write(value + "\n")
