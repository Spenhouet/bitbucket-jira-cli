"""`bj issue` — Jira issues (search, view, create, edit, transition, comment)."""

from __future__ import annotations

from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.api.adf import text_to_adf
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.errors import BranchKeyError
from bitbucket_jira_cli.git import current_branch
from bitbucket_jira_cli.git import parse_branch_key
from bitbucket_jira_cli.jira_ops import transition_to
from bitbucket_jira_cli.render import render_issue
from bitbucket_jira_cli.render import render_issue_list
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

issue_app = typer.Typer(help="Manage Jira issues.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]


def _resolve_key(key: str | None, config: Config) -> str:
    if key:
        return key.upper()
    branch = current_branch()
    derived = parse_branch_key(branch, config.branch_key) if branch else None
    if not derived:
        msg = "No issue key given and none found in the current branch name."
        raise BranchKeyError(msg)
    return derived


@issue_app.command(name="list")
def list_issues(
    jql: Annotated[str | None, typer.Option("--jql", "-q", help="Raw JQL query.")] = None,
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
    query = jql or (" AND ".join(clauses) if clauses else "order by updated DESC")

    async def _run() -> None:
        async with jira_client(config) as client:
            issues = await client.search(query, limit=limit)
            if emit(issues, as_json=as_json, jq=jq):
                return
            render_issue_list(issues)

    run(_run())


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

    async def _run() -> None:
        async with jira_client(config) as client:
            issue = await client.get_issue(resolved, fields=["*all"])
            comment_list = await client.list_comments(resolved) if comments else None
            if emit(issue, as_json=as_json, jq=jq):
                return
            render_issue(issue, comment_list)

    run(_run())


@issue_app.command()
def create(
    project: Annotated[str | None, typer.Option("--project", "-p", help="Project key.")] = None,
    issue_type: Annotated[str, typer.Option("--type", "-t", help="Issue type.")] = "Task",
    summary: Annotated[str | None, typer.Option("--summary", "-s", help="Summary/title.")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="Description.")] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Create a Jira issue."""
    config = load_config()
    proj = project
    if not proj:
        msg = "A project key is required: pass --project."
        raise BranchKeyError(msg)
    final_summary = summary or typer.prompt("Summary")
    fields: dict[str, Any] = {
        "project": {"key": proj},
        "issuetype": {"name": issue_type},
        "summary": final_summary,
    }
    if body:
        fields["description"] = text_to_adf(body)

    async def _run() -> None:
        async with jira_client(config) as client:
            created = await client.create_issue({"fields": fields})
            if emit(created, as_json=as_json, jq=jq):
                return
            success(f"Created {created.get('key')}")

    run(_run())


@issue_app.command()
def edit(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    summary: Annotated[str | None, typer.Option("--summary", "-s", help="New summary.")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="New description.")] = None,
) -> None:
    """Edit a Jira issue's fields."""
    config = load_config()
    resolved = _resolve_key(key, config)
    fields: dict[str, Any] = {}
    if summary:
        fields["summary"] = summary
    if body:
        fields["description"] = text_to_adf(body)
    if not fields:
        msg = "Nothing to edit: pass --summary and/or --body."
        raise BranchKeyError(msg)

    async def _run() -> None:
        async with jira_client(config) as client:
            await client.edit_issue(resolved, {"fields": fields})
            success(f"Updated {resolved}")

    run(_run())


@issue_app.command()
def comment(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="Comment text.")] = None,
) -> None:
    """Add a comment to a Jira issue."""
    config = load_config()
    resolved = _resolve_key(key, config)
    text = body or typer.prompt("Comment")

    async def _run() -> None:
        async with jira_client(config) as client:
            await client.add_comment(resolved, text_to_adf(text))
            success(f"Commented on {resolved}")

    run(_run())


@issue_app.command()
def transition(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    state: Annotated[
        str | None, typer.Argument(help="Target state (omit to list available).")
    ] = None,
) -> None:
    """Transition an issue, or list available transitions when no state is given."""
    config = load_config()
    resolved = _resolve_key(key, config)

    async def _run() -> None:
        async with jira_client(config) as client:
            if state is None:
                transitions = await client.get_transitions(resolved)
                console.print(f"[bold]Available transitions for {resolved}[/bold]")
                for t in transitions:
                    console.print(f"  {t.get('name')} → {t.get('to', {}).get('name', '?')}")
                return
            if await transition_to(client, resolved, state):
                success(f"{resolved} → {state}")
            else:
                msg = f"No transition to '{state}' is available for {resolved}."
                raise BranchKeyError(msg)

    run(_run())


@issue_app.command()
def close(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
) -> None:
    """Close a Jira issue (transition to the configured done state)."""
    config = load_config()
    resolved = _resolve_key(key, config)
    target = config.transitions.on_pr_merge or "Done"

    async def _run() -> None:
        async with jira_client(config) as client:
            if await transition_to(client, resolved, target):
                success(f"{resolved} → {target}")
            else:
                msg = f"No transition to '{target}' is available for {resolved}."
                raise BranchKeyError(msg)

    run(_run())
