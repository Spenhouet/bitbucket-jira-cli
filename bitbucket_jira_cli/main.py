"""CLI entry point.

This is the bootstrap scaffold: the command tree is declared so `bj --help`
renders the intended surface, but no backend calls are wired yet. Feature code
lands per the plan in docs/plan/command-mapping.md.
"""

from typing import Annotated

import typer

from bitbucket_jira_cli import __version__

app = typer.Typer(
    name="bj",
    help="A gh-style CLI for Bitbucket (PRs, repos, pipelines) and Jira (issues).",
    no_args_is_help=True,
    add_completion=True,
)

# Command groups mirror gh's noun-first ergonomics. They are registered here as
# empty sub-apps so the surface is visible in `--help`; commands are added as
# features are implemented.
auth_app = typer.Typer(help="Authenticate bj with Bitbucket and Jira.", no_args_is_help=True)
repo_app = typer.Typer(help="Work with Bitbucket repositories.", no_args_is_help=True)
pr_app = typer.Typer(help="Manage Bitbucket pull requests.", no_args_is_help=True)
issue_app = typer.Typer(help="Manage Jira issues.", no_args_is_help=True)
pipeline_app = typer.Typer(help="Work with Bitbucket Pipelines.", no_args_is_help=True)

app.add_typer(auth_app, name="auth")
app.add_typer(repo_app, name="repo")
app.add_typer(pr_app, name="pr")
app.add_typer(issue_app, name="issue")
app.add_typer(pipeline_app, name="pipeline")


def _version_callback(value: bool) -> None:  # noqa: FBT001
    if value:
        typer.echo(f"bitbucket-jira-cli {__version__}")
        raise typer.Exit


@app.callback()
def main(
    _version: Annotated[  # noqa: FBT002
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


if __name__ == "__main__":
    app()
