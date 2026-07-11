"""Human-facing rich rendering for PRs, issues, repos and pipelines."""

from __future__ import annotations

from typing import Any

from rich.table import Table

from bitbucket_jira_cli.api.adf import adf_to_text
from bitbucket_jira_cli.ui import console

_PR_STATE_COLORS = {
    "OPEN": "green",
    "MERGED": "magenta",
    "DECLINED": "red",
    "SUPERSEDED": "yellow",
}


def _state(text: str, color_map: dict[str, str]) -> str:
    color = color_map.get(text.upper(), "white")
    return f"[{color}]{text}[/{color}]"


# -- pull requests ----------------------------------------------------------
def pr_row_title(pr: dict[str, Any]) -> str:
    return str(pr.get("title", ""))


def render_pr_list(prs: list[dict[str, Any]]) -> None:
    if not prs:
        console.print("[dim]No pull requests found.[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Title")
    table.add_column("State")
    table.add_column("Source", style="dim")
    for pr in prs:
        table.add_row(
            str(pr.get("id", "")),
            pr_row_title(pr),
            _state(str(pr.get("state", "")), _PR_STATE_COLORS),
            str(pr.get("source", {}).get("branch", {}).get("name", "")),
        )
    console.print(table)


def render_pr(pr: dict[str, Any], comments: list[dict[str, Any]] | None = None) -> None:
    author = pr.get("author", {}).get("display_name", "?")
    src = pr.get("source", {}).get("branch", {}).get("name", "?")
    dst = pr.get("destination", {}).get("branch", {}).get("name", "?")
    console.print(f"[bold]#{pr.get('id')} {pr.get('title')}[/bold]")
    console.print(
        f"{_state(str(pr.get('state', '')), _PR_STATE_COLORS)} · {author} · {src} → {dst}"
    )
    url = pr.get("links", {}).get("html", {}).get("href")
    if url:
        console.print(f"[dim]{url}[/dim]")
    reviewers = pr.get("participants", []) or []
    approvals = [p for p in reviewers if p.get("approved")]
    if approvals:
        names = ", ".join(p.get("user", {}).get("display_name", "?") for p in approvals)
        console.print(f"[green]Approved by:[/green] {names}")
    summary = pr.get("summary", {}).get("raw") or pr.get("description")
    if summary:
        console.print()
        console.print(summary)
    if comments:
        console.print("\n[bold]Comments[/bold]")
        for c in comments:
            who = c.get("user", {}).get("display_name", "?")
            body = c.get("content", {}).get("raw", "")
            console.print(f"[cyan]{who}[/cyan]: {body}")


# -- Jira issues ------------------------------------------------------------
def render_issue_list(issues: list[dict[str, Any]]) -> None:
    if not issues:
        console.print("[dim]No issues found.[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    table.add_column("Key", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Status")
    table.add_column("Summary")
    for issue in issues:
        fields = issue.get("fields", {})
        table.add_row(
            issue.get("key", ""),
            fields.get("issuetype", {}).get("name", ""),
            fields.get("status", {}).get("name", ""),
            fields.get("summary", ""),
        )
    console.print(table)


def render_issue(issue: dict[str, Any], comments: list[dict[str, Any]] | None = None) -> None:
    fields = issue.get("fields", {})
    console.print(f"[bold]{issue.get('key')} {fields.get('summary', '')}[/bold]")
    status = fields.get("status", {}).get("name", "?")
    issue_type = fields.get("issuetype", {}).get("name", "?")
    assignee = (fields.get("assignee") or {}).get("displayName", "Unassigned")
    console.print(f"[yellow]{status}[/yellow] · {issue_type} · assignee: {assignee}")
    description = fields.get("description")
    if description:
        console.print()
        console.print(adf_to_text(description).strip())
    if comments:
        console.print("\n[bold]Comments[/bold]")
        for c in comments:
            who = c.get("author", {}).get("displayName", "?")
            console.print(f"[cyan]{who}[/cyan]: {adf_to_text(c.get('body')).strip()}")


# -- repositories -----------------------------------------------------------
def render_repo_list(repos: list[dict[str, Any]]) -> None:
    if not repos:
        console.print("[dim]No repositories found.[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    table.add_column("Name", style="cyan")
    table.add_column("Access", style="dim")
    table.add_column("Description")
    for repo in repos:
        table.add_row(
            repo.get("full_name", repo.get("name", "")),
            "private" if repo.get("is_private") else "public",
            (repo.get("description") or "").splitlines()[0] if repo.get("description") else "",
        )
    console.print(table)


def render_repo(repo: dict[str, Any]) -> None:
    console.print(f"[bold]{repo.get('full_name', repo.get('name'))}[/bold]")
    if repo.get("description"):
        console.print(repo["description"])
    console.print(
        f"[dim]{'private' if repo.get('is_private') else 'public'} · "
        f"{repo.get('language') or 'n/a'} · "
        f"main: {repo.get('mainbranch', {}).get('name', '?')}[/dim]"
    )
    url = repo.get("links", {}).get("html", {}).get("href")
    if url:
        console.print(f"[dim]{url}[/dim]")


# -- pipelines --------------------------------------------------------------
def _pipeline_status(pipeline: dict[str, Any]) -> str:
    state = pipeline.get("state", {})
    name = state.get("result", {}).get("name") or state.get("name", "")
    color = {
        "SUCCESSFUL": "green",
        "FAILED": "red",
        "IN_PROGRESS": "yellow",
        "STOPPED": "yellow",
        "PENDING": "cyan",
    }.get(name.upper(), "white")
    return f"[{color}]{name}[/{color}]"


def render_pipeline_list(pipelines: list[dict[str, Any]]) -> None:
    if not pipelines:
        console.print("[dim]No pipelines found.[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Status")
    table.add_column("Ref", style="dim")
    table.add_column("Trigger", style="dim")
    for pipeline in pipelines:
        target = pipeline.get("target", {})
        table.add_row(
            str(pipeline.get("build_number", "")),
            _pipeline_status(pipeline),
            target.get("ref_name", ""),
            pipeline.get("trigger", {}).get("name", ""),
        )
    console.print(table)


def render_pipeline(pipeline: dict[str, Any], steps: list[dict[str, Any]] | None = None) -> None:
    console.print(
        f"[bold]Pipeline #{pipeline.get('build_number')}[/bold] {_pipeline_status(pipeline)}"
    )
    target = pipeline.get("target", {})
    console.print(
        f"[dim]ref: {target.get('ref_name', '?')} · uuid: {pipeline.get('uuid', '')}[/dim]"
    )
    if steps:
        console.print("\n[bold]Steps[/bold]")
        for step in steps:
            console.print(f"  {_pipeline_status(step)} {step.get('name', '(unnamed)')}")
