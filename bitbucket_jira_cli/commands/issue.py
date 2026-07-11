"""`bj issue` — Jira issues (search, view, create, edit, transition, comment)."""

from __future__ import annotations

from typing import Annotated
from typing import Any

import questionary
import typer

from bitbucket_jira_cli.api.adf import text_to_adf
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.errors import BranchKeyError
from bitbucket_jira_cli.git import current_branch
from bitbucket_jira_cli.git import parse_branch_key
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import edit_text
from bitbucket_jira_cli.interaction import is_interactive
from bitbucket_jira_cli.interaction import require_input
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.interaction import select
from bitbucket_jira_cli.jira_ops import transition_to
from bitbucket_jira_cli.render import render_issue
from bitbucket_jira_cli.render import render_issue_list
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

issue_app = typer.Typer(help="Manage Jira issues.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
EditorOpt = Annotated[bool, typer.Option("--editor", "-e", help="Write the body in $EDITOR.")]
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]


def _resolve_key(key: str | None, config: Config) -> str:
    if key:
        return key.upper()
    branch = current_branch()
    derived = parse_branch_key(branch, config.branch_key) if branch else None
    if not derived:
        msg = "No issue key given and none found in the current branch name."
        raise BranchKeyError(msg)
    return derived


def _body_from(body: str | None, *, editor: bool) -> str | None:
    if body is not None:
        return body
    if editor:
        return edit_text("") or None
    return None


@issue_app.command(name="list")
def list_issues(
    jql: Annotated[str | None, typer.Option("--jql", help="Raw JQL query.")] = None,
    status: Annotated[str | None, typer.Option("--status", "-s", help="Filter by status.")] = None,
    assignee: Annotated[
        str | None, typer.Option("--assignee", "-a", help="Filter by assignee (accountId or 'me').")
    ] = None,
    issue_type: Annotated[
        str | None, typer.Option("--type", "-t", help="Filter by issue type.")
    ] = None,
    project: Annotated[
        str | None, typer.Option("--project", "-p", help="Filter by project key.")
    ] = None,
    label: Annotated[str | None, typer.Option("--label", "-l", help="Filter by label.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", help="Max results.")] = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search Jira issues with JQL or shorthand filters."""
    config = load_config()
    clauses: list[str] = []
    if project:
        clauses.append(f'project = "{project}"')
    if status:
        clauses.append(f'status = "{status}"')
    if assignee:
        clauses.append(
            "assignee = currentUser()" if assignee == "me" else f'assignee = "{assignee}"'
        )
    if issue_type:
        clauses.append(f'issuetype = "{issue_type}"')
    if label:
        clauses.append(f'labels = "{label}"')
    # `/search/jql` rejects unbounded queries, so default to the current user's
    # issues (a bounded restriction) when no --jql/filters are given.
    if jql:
        query = jql
    elif clauses:
        query = " AND ".join(clauses) + " ORDER BY updated DESC"
    else:
        query = "assignee = currentUser() ORDER BY updated DESC"

    async def _run() -> list[dict[str, Any]]:
        async with jira_client(config) as client:
            return await client.search(query, limit=limit)

    issues = run_with_status("Searching…", _run())
    if not emit(issues, as_json=as_json, jq=jq):
        render_issue_list(issues)


@issue_app.command()
def view(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    comments: Annotated[bool, typer.Option("--comments", "-c", help="Show comments.")] = False,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """View a Jira issue."""
    config = load_config()
    resolved = _resolve_key(key, config)

    async def _run() -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
        async with jira_client(config) as client:
            issue = await client.get_issue(resolved, fields=["*all"])
            comment_list = await client.list_comments(resolved) if comments else None
            return issue, comment_list

    issue, comment_list = run_with_status("Loading issue…", _run())
    if not emit(issue, as_json=as_json, jq=jq):
        render_issue(issue, comment_list)


@issue_app.command()
def create(
    project: Annotated[str | None, typer.Option("--project", "-p", help="Project key.")] = None,
    issue_type: Annotated[str, typer.Option("--type", "-t", help="Issue type.")] = "Task",
    summary: Annotated[str | None, typer.Option("--summary", "-s", help="Summary/title.")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="Description.")] = None,
    editor: EditorOpt = False,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Create a Jira issue."""
    config = load_config()
    proj = require_input(project, flag="--project", label="Project key")
    final_summary = require_input(summary, flag="--summary", label="Summary")
    fields: dict[str, Any] = {
        "project": {"key": proj},
        "issuetype": {"name": issue_type},
        "summary": final_summary,
    }
    description = _body_from(body, editor=editor)
    if description:
        fields["description"] = text_to_adf(description)

    async def _run() -> dict[str, Any]:
        async with jira_client(config) as client:
            return await client.create_issue({"fields": fields})

    created = run_with_status("Creating issue…", _run())
    if not emit(created, as_json=as_json, jq=jq):
        success(f"Created {created.get('key')}")


@issue_app.command()
def edit(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    summary: Annotated[str | None, typer.Option("--summary", "-s", help="New summary.")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="New description.")] = None,
    editor: EditorOpt = False,
) -> None:
    """Edit a Jira issue's fields."""
    config = load_config()
    resolved = _resolve_key(key, config)
    fields: dict[str, Any] = {}
    if summary:
        fields["summary"] = summary
    description = _body_from(body, editor=editor)
    if description:
        fields["description"] = text_to_adf(description)
    if not fields:
        msg = "Nothing to edit: pass --summary and/or --body (or --editor)."
        raise BranchKeyError(msg)

    async def _run() -> None:
        async with jira_client(config) as client:
            await client.edit_issue(resolved, {"fields": fields})

    run_with_status("Updating…", _run())
    success(f"Updated {resolved}")


@issue_app.command()
def comment(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="Comment text.")] = None,
    editor: EditorOpt = False,
) -> None:
    """Add a comment to a Jira issue."""
    config = load_config()
    resolved = _resolve_key(key, config)
    text = require_input(body, flag="--body", label="Comment", editor=editor)

    async def _run() -> None:
        async with jira_client(config) as client:
            await client.add_comment(resolved, text_to_adf(text))

    run_with_status("Adding comment…", _run())
    success(f"Commented on {resolved}")


@issue_app.command()
def transition(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    state: Annotated[
        str | None, typer.Argument(help="Target state (omit to choose interactively).")
    ] = None,
) -> None:
    """Transition an issue, choosing from the available states when none is given."""
    config = load_config()
    resolved = _resolve_key(key, config)

    async def _fetch() -> list[dict[str, Any]]:
        async with jira_client(config) as client:
            return await client.get_transitions(resolved)

    transitions = run_with_status("Loading transitions…", _fetch())
    if state is None:
        if not transitions:
            console.print(f"[dim]No transitions available for {resolved}.[/dim]")
            return
        if not is_interactive():
            console.print(f"[bold]Available transitions for {resolved}[/bold]")
            for t in transitions:
                console.print(f"  {t.get('name')} → {t.get('to', {}).get('name', '?')}")
            return
        state = select(
            f"Transition {resolved} to",
            [
                questionary.Choice(
                    f"{t.get('name')} → {t.get('to', {}).get('name', '?')}", value=t.get("name")
                )
                for t in transitions
            ],
        )

    async def _do() -> bool:
        async with jira_client(config) as client:
            return await transition_to(client, resolved, state)

    if run_with_status("Transitioning…", _do()):
        success(f"{resolved} → {state}")
    else:
        msg = f"No transition to '{state}' is available for {resolved}."
        raise BranchKeyError(msg)


@issue_app.command()
def close(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    yes: YesOpt = False,
) -> None:
    """Close a Jira issue (transition to the configured done state)."""
    config = load_config()
    resolved = _resolve_key(key, config)
    target = config.transitions.on_pr_merge or "Done"
    if not confirm(f"Close {resolved} (transition to '{target}')?", yes=yes):
        raise typer.Abort

    async def _run() -> bool:
        async with jira_client(config) as client:
            return await transition_to(client, resolved, target)

    if run_with_status("Closing…", _run()):
        success(f"{resolved} → {target}")
    else:
        msg = f"No transition to '{target}' is available for {resolved}."
        raise BranchKeyError(msg)
