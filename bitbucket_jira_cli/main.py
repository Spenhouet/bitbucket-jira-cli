"""CLI entry point: assembles the command tree and handles top-level errors."""

from __future__ import annotations

import shlex
import sys
from typing import Annotated

import typer

from bitbucket_jira_cli import __version__
from bitbucket_jira_cli.auth.commands import auth_app
from bitbucket_jira_cli.commands.alias import alias_app
from bitbucket_jira_cli.commands.board import board_app
from bitbucket_jira_cli.commands.config import config_app
from bitbucket_jira_cli.commands.issue import issue_app
from bitbucket_jira_cli.commands.misc import api
from bitbucket_jira_cli.commands.misc import browse
from bitbucket_jira_cli.commands.misc import status
from bitbucket_jira_cli.commands.pipeline import pipeline_app
from bitbucket_jira_cli.commands.pr import pr_app
from bitbucket_jira_cli.commands.release import release_app
from bitbucket_jira_cli.commands.repo import repo_app
from bitbucket_jira_cli.commands.ruleset import ruleset_app
from bitbucket_jira_cli.commands.search import search_app
from bitbucket_jira_cli.commands.skill import skill_app
from bitbucket_jira_cli.commands.snippet import snippet_app
from bitbucket_jira_cli.commands.sshkey import sshkey_app
from bitbucket_jira_cli.commands.variable import variable_app
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.ui import print_error

app = typer.Typer(
    name="bj",
    help="A gh-style CLI for Bitbucket (PRs, repos, pipelines) and Jira (issues).",
    no_args_is_help=True,
    add_completion=True,
)

app.add_typer(auth_app, name="auth")
app.add_typer(repo_app, name="repo")
app.add_typer(pr_app, name="pr")
app.add_typer(issue_app, name="issue")
app.add_typer(pipeline_app, name="pipeline")
app.add_typer(skill_app, name="skill")
app.add_typer(release_app, name="release")
app.add_typer(variable_app, name="variable")
app.add_typer(config_app, name="config")
app.add_typer(search_app, name="search")
app.add_typer(sshkey_app, name="ssh-key")
app.add_typer(snippet_app, name="snippet")
app.add_typer(ruleset_app, name="ruleset")
app.add_typer(board_app, name="board")
app.add_typer(alias_app, name="alias")
app.command(name="browse")(browse)
app.command(name="api")(api)
app.command(name="status")(status)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"bitbucket-jira-cli {__version__}")
        raise typer.Exit


@app.callback()
def main(
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """A gh-style CLI for Bitbucket and Jira."""


def _expand_alias(argv: list[str]) -> list[str]:
    """Expand a leading user alias (from config) into its command, gh-style."""
    if not argv or argv[0].startswith("-"):
        return argv
    try:
        aliases = load_config().aliases
    except (OSError, ValueError):
        return argv
    expansion = aliases.get(argv[0])
    if not expansion:
        return argv
    return [*shlex.split(expansion), *argv[1:]]


def cli() -> None:
    """Console-script entry point: run the app, print BjErrors cleanly."""
    sys.argv = [sys.argv[0], *_expand_alias(sys.argv[1:])]
    try:
        app()
    except BjError as exc:
        print_error(str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    cli()
