"""`bj issue` — Jira issues (search, view, create, edit, transition, comment)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
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
from bitbucket_jira_cli.git import create_branch
from bitbucket_jira_cli.git import current_branch
from bitbucket_jira_cli.git import parse_branch_key
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import edit_text
from bitbucket_jira_cli.interaction import is_interactive
from bitbucket_jira_cli.interaction import require_input
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.interaction import select
from bitbucket_jira_cli.jira_fields import build_index
from bitbucket_jira_cli.jira_fields import coerce_value
from bitbucket_jira_cli.jira_fields import is_user_type
from bitbucket_jira_cli.jira_fields import resolve_field
from bitbucket_jira_cli.jira_ops import transition_to
from bitbucket_jira_cli.render import field_value_str
from bitbucket_jira_cli.render import render_issue
from bitbucket_jira_cli.render import render_issue_fields
from bitbucket_jira_cli.render import render_issue_list
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

if TYPE_CHECKING:
    from bitbucket_jira_cli.api.jira import JiraClient

issue_app = typer.Typer(help="Manage Jira issues.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
EditorOpt = Annotated[bool, typer.Option("--editor", "-e", help="Write the body in $EDITOR.")]
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]
_ALLOWED_TRUNC = 40


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


async def _resolve_account_id(client: JiraClient, query: str, issue_key: str) -> str:
    if query.lower() == "me":
        return str((await client.myself())["accountId"])
    users = await client.search_assignable_users(query, issue_key=issue_key)
    if not users:
        msg = f"No assignable user matches '{query}'."
        raise BranchKeyError(msg)
    return str(users[0]["accountId"])


def _label_verbs(labels: list[str]) -> list[dict[str, str]]:
    verbs: list[dict[str, str]] = []
    for raw in labels:
        if raw.startswith("-"):
            verbs.append({"remove": raw[1:]})
        else:
            verbs.append({"add": raw.removeprefix("+")})
    return verbs


@issue_app.command()
def fields(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List the editable fields on an issue (name, id, type, value, allowed values)."""
    config = load_config()
    resolved = _resolve_key(key, config)

    async def _run() -> tuple[dict[str, Any], dict[str, Any]]:
        async with jira_client(config) as client:
            editmeta = await client.get_editmeta(resolved)
            issue = await client.get_issue(resolved, fields=["*all"], expand=["schema"])
            return editmeta, issue.get("fields", {})

    editmeta, values = run_with_status("Loading fields…", _run())
    if emit(editmeta, as_json=as_json, jq=jq):
        return
    rows = []
    for field_id, meta in sorted(editmeta.items(), key=lambda kv: kv[1].get("name", "")):
        schema = meta.get("schema", {})
        type_str = schema.get("type", "")
        if schema.get("items"):
            type_str += f"[{schema['items']}]"
        allowed = ", ".join(
            str(a.get("value") or a.get("name") or a.get("id"))
            for a in meta.get("allowedValues", [])
        )
        rows.append(
            {
                "name": meta.get("name", field_id),
                "id": field_id,
                "type": type_str,
                "value": field_value_str(values.get(field_id)),
                "allowed": (allowed[:_ALLOWED_TRUNC] + "…")
                if len(allowed) > _ALLOWED_TRUNC
                else allowed,
            }
        )
    render_issue_fields(rows)


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
    assignee: Annotated[
        str | None, typer.Option("--assignee", "-a", help="Assignee (name/email, or 'me').")
    ] = None,
    label: Annotated[list[str] | None, typer.Option("--label", "-l", help="Label.")] = None,
    priority: Annotated[str | None, typer.Option("--priority", help="Priority name.")] = None,
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
    if priority:
        fields["priority"] = {"name": priority}
    if label:
        fields["labels"] = [ll.removeprefix("+") for ll in label]

    async def _run() -> dict[str, Any]:
        async with jira_client(config) as client:
            if assignee:
                # Resolve against the project's assignable users (no issue yet).
                users = await client.search_assignable_users(assignee, issue_key=f"{proj}-1")
                if users:
                    fields["assignee"] = {"accountId": users[0]["accountId"]}
            return await client.create_issue({"fields": fields})

    created = run_with_status("Creating issue…", _run())
    if not emit(created, as_json=as_json, jq=jq):
        success(f"Created {created.get('key')}")


async def _apply_field_specs(
    client: JiraClient, resolved: str, specs: list[str], fields: dict[str, Any]
) -> None:
    editmeta = await client.get_editmeta(resolved)
    index = build_index(editmeta)
    for spec in specs:
        name, sep, value = spec.partition("=")
        if not sep:
            msg = f"--field must be NAME=VALUE, got '{spec}'."
            raise BranchKeyError(msg)
        field_id, meta = resolve_field(name.strip(), index)
        if is_user_type(meta.get("schema", {})):
            fields[field_id] = {
                "accountId": await _resolve_account_id(client, value.strip(), resolved)
            }
        else:
            fields[field_id] = coerce_value(value.strip(), meta)


@issue_app.command()
def edit(  # noqa: C901 — orchestrates many optional field updates.
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    summary: Annotated[str | None, typer.Option("--summary", "-s", help="New summary.")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="New description.")] = None,
    editor: EditorOpt = False,
    assignee: Annotated[
        str | None, typer.Option("--assignee", "-a", help="Assignee (name/email, or 'me').")
    ] = None,
    label: Annotated[
        list[str] | None, typer.Option("--label", "-l", help="Label; prefix '-' to remove.")
    ] = None,
    priority: Annotated[str | None, typer.Option("--priority", help="Priority name.")] = None,
    field: Annotated[
        list[str] | None,
        typer.Option("--field", help="Set any field: 'Name=Value' (repeatable)."),
    ] = None,
) -> None:
    """Edit a Jira issue: summary, description, assignee, labels, priority, or any --field."""
    config = load_config()
    resolved = _resolve_key(key, config)
    if not (summary or body or editor or assignee or label or priority or field):
        msg = "Nothing to edit. Pass --summary/--body/--assignee/--label/--priority/--field."
        raise BranchKeyError(msg)
    description = _body_from(body, editor=editor)

    async def _run() -> None:
        async with jira_client(config) as client:
            fields: dict[str, Any] = {}
            update: dict[str, Any] = {}
            if summary:
                fields["summary"] = summary
            if description is not None:
                fields["description"] = text_to_adf(description)
            if priority:
                fields["priority"] = {"name": priority}
            if assignee:
                fields["assignee"] = {
                    "accountId": await _resolve_account_id(client, assignee, resolved)
                }
            if label:
                update["labels"] = _label_verbs(label)
            if field:
                await _apply_field_specs(client, resolved, field, fields)
            payload: dict[str, Any] = {}
            if fields:
                payload["fields"] = fields
            if update:
                payload["update"] = update
            await client.edit_issue(resolved, payload)

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


def _slugify(text: str, *, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].rstrip("-")


@issue_app.command()
def develop(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    base: Annotated[str | None, typer.Option("--base", help="Base ref to branch from.")] = None,
    name: Annotated[str | None, typer.Option("--name", help="Override the branch name.")] = None,
    checkout: Annotated[
        bool, typer.Option("--checkout/--no-checkout", help="Check out the new branch.")
    ] = True,
) -> None:
    """Create a local git branch for an issue (its key drives branch-key automation)."""
    config = load_config()
    resolved = _resolve_key(key, config)

    async def _run() -> dict[str, Any]:
        async with jira_client(config) as client:
            return await client.get_issue(resolved, fields=["summary"])

    issue = run_with_status("Loading issue…", _run())
    summary = issue.get("fields", {}).get("summary", "")
    branch = name or f"{resolved}-{_slugify(summary)}".rstrip("-")
    if not checkout:
        console.print(branch)
        return
    if not create_branch(branch, base=base):
        msg = f"Could not create branch '{branch}' (already exists, or not in a git repo)."
        raise BranchKeyError(msg)
    success(f"Created and checked out branch '{branch}' for {resolved}")


@issue_app.command()
def delete(
    key: Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")] = None,
    yes: YesOpt = False,
) -> None:
    """Delete a Jira issue (irreversible)."""
    config = load_config()
    resolved = _resolve_key(key, config)
    if not confirm(f"Delete {resolved}? This cannot be undone.", yes=yes):
        raise typer.Abort

    async def _run() -> None:
        async with jira_client(config) as client:
            await client.delete_issue(resolved)

    run_with_status("Deleting…", _run())
    success(f"Deleted {resolved}")


@issue_app.command()
def status(
    limit: Annotated[int, typer.Option("--limit", "-L", help="Max results.")] = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Show open Jira issues assigned to you."""
    config = load_config()
    jql = "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"

    async def _run() -> list[dict[str, Any]]:
        async with jira_client(config) as client:
            return await client.search(jql, limit=limit)

    issues = run_with_status("Loading your issues…", _run())
    if not emit(issues, as_json=as_json, jq=jq):
        render_issue_list(issues)
