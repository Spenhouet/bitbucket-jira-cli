"""`bj alias` - user-defined command shortcuts (the gh alias analog).

Aliases are stored in config.yml and expanded before dispatch, e.g.
`bj alias set prs 'pr list --state open'` makes `bj prs` run that command.
"""

from __future__ import annotations

from typing import Annotated

import typer

from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.config import save_config
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

alias_app = typer.Typer(help="Create command shortcuts.", no_args_is_help=True)

# Top-level names an alias must not shadow (kept in sync with main.py registration).
RESERVED = {
    "auth", "repo", "pr", "issue", "pipeline", "skill", "release", "variable",
    "config", "search", "ssh-key", "snippet", "ruleset", "board",
    "alias", "browse", "api", "status",
}


@alias_app.command(name="set")
def set_alias(
    name: Annotated[str, typer.Argument(help="Alias name.")],
    expansion: Annotated[str, typer.Argument(help="Command it expands to, e.g. 'pr list'.")],
) -> None:
    """Create or update an alias."""
    if name in RESERVED:
        msg = f"'{name}' is a built-in command and cannot be an alias."
        raise BjError(msg)
    config = load_config()
    config.aliases[name] = expansion
    save_config(config)
    success(f"Set alias {name!r} -> {expansion!r}")


@alias_app.command(name="list")
def list_aliases() -> None:
    """List defined aliases."""
    aliases = load_config().aliases
    if not aliases:
        console.print("[dim]No aliases.[/dim]")
        return
    for name, expansion in aliases.items():
        console.print(f"[cyan]{name}[/cyan] = {expansion}")


@alias_app.command(name="delete")
def delete_alias(name: Annotated[str, typer.Argument(help="Alias to delete.")]) -> None:
    """Delete an alias."""
    config = load_config()
    if name not in config.aliases:
        msg = f"No alias named '{name}'."
        raise BjError(msg)
    del config.aliases[name]
    save_config(config)
    success(f"Deleted alias {name!r}")
