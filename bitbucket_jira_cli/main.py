"""CLI entry point: assembles the command tree and handles top-level errors."""

from __future__ import annotations

from typing import Annotated

import typer

from bitbucket_jira_cli import __version__
from bitbucket_jira_cli.auth.commands import auth_app
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.ui import print_error

app = typer.Typer(
    name="bj",
    help="A gh-style CLI for Bitbucket (PRs, repos, pipelines) and Jira (issues).",
    no_args_is_help=True,
    add_completion=True,
)

app.add_typer(auth_app, name="auth")

# Placeholder groups — implemented in follow-up modules. Kept registered so
# `bj --help` renders the full intended surface.
repo_app = typer.Typer(help="Work with Bitbucket repositories.", no_args_is_help=True)
pr_app = typer.Typer(help="Manage Bitbucket pull requests.", no_args_is_help=True)
issue_app = typer.Typer(help="Manage Jira issues.", no_args_is_help=True)
pipeline_app = typer.Typer(help="Work with Bitbucket Pipelines.", no_args_is_help=True)
app.add_typer(repo_app, name="repo")
app.add_typer(pr_app, name="pr")
app.add_typer(issue_app, name="issue")
app.add_typer(pipeline_app, name="pipeline")


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


def cli() -> None:
    """Console-script entry point: run the app, print BjErrors cleanly."""
    try:
        app()
    except BjError as exc:
        print_error(str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    cli()
