"""`bj pr` — Bitbucket pull requests, with branch-key Jira automation."""

from __future__ import annotations

import webbrowser
from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.api.jira import JiraClient
from bitbucket_jira_cli.auth.store import get_token
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.commands._common import resolve_repo
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import bitbucket_authorization
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.git import RepoRef
from bitbucket_jira_cli.git import checkout_branch
from bitbucket_jira_cli.git import current_branch
from bitbucket_jira_cli.git import last_commit_body
from bitbucket_jira_cli.git import last_commit_subject
from bitbucket_jira_cli.git import parse_branch_key
from bitbucket_jira_cli.jira_ops import link_pr
from bitbucket_jira_cli.jira_ops import transition_to
from bitbucket_jira_cli.render import render_pr
from bitbucket_jira_cli.render import render_pr_list
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

pr_app = typer.Typer(help="Manage Bitbucket pull requests.", no_args_is_help=True)

RepoOpt = Annotated[str | None, typer.Option("--repo", "-R", help="Target repo as WORKSPACE/REPO.")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
WebOpt = Annotated[bool, typer.Option("--web", "-w", help="Open in the browser.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


def _jira_if_configured(config: Config) -> JiraClient | None:
    from bitbucket_jira_cli.auth.store import basic_header

    if not (config.jira.site and config.jira.email and get_token("jira")):
        return None
    return JiraClient(config.jira.site, basic_header(config.jira.email, get_token("jira") or ""))


def _reviewer_ref(value: str) -> dict[str, str]:
    return {"uuid": value} if value.startswith("{") else {"account_id": value}


def _open_web(url: str | None) -> None:
    if not url:
        msg = "No web URL available."
        raise BjError(msg)
    webbrowser.open(url)
    console.print(f"[dim]Opening {url}[/dim]")


async def _pr_for_branch(client: BitbucketClient, ref: RepoRef, branch: str) -> int:
    prs = await client.list_prs(ref.workspace, ref.repo_slug, source_branch=branch, limit=1)
    if not prs:
        msg = f"No open pull request found for branch '{branch}'."
        raise BjError(msg)
    return int(prs[0]["id"])


async def _resolve_id(client: BitbucketClient, ref: RepoRef, pr_id: int | None) -> int:
    if pr_id is not None:
        return pr_id
    branch = current_branch()
    if not branch:
        msg = "No PR id given and no current git branch to infer from."
        raise BjError(msg)
    return await _pr_for_branch(client, ref, branch)


async def _resolve_title_body(
    jira: JiraClient | None,
    key: str | None,
    *,
    title: str | None,
    body: str | None,
    source: str,
    fill: bool,
) -> tuple[str, str]:
    final_title = title
    final_body = body or ""
    if fill:
        final_title = final_title or last_commit_subject()
        final_body = final_body or (last_commit_body() or "")
    if not final_title and key and jira:
        issue = await jira.get_issue(key, fields=["summary"])
        final_title = f"{key}: {issue.get('fields', {}).get('summary', '')}".strip()
    final_title = final_title or source
    if key and jira and key not in final_body:
        final_body = (final_body + f"\n\nJira: {key}").strip()
    return final_title, final_body


async def _apply_jira_on_create(
    jira: JiraClient, key: str, target: str | None, url: str, title: str
) -> None:
    await link_pr(jira, key, url, title)
    if target and await transition_to(jira, key, target):
        console.print(f"[green]✓[/green] {key} → {target}")
    elif target:
        console.print(f"[yellow]![/yellow] {key}: no '{target}' transition available")


@pr_app.command()
def create(  # noqa: PLR0913 — mirrors `gh pr create`, which has many flags.
    title: Annotated[str | None, typer.Option("--title", "-t", help="PR title.")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="PR description.")] = None,
    base: Annotated[str | None, typer.Option("--base", "-B", help="Target branch.")] = None,
    head: Annotated[str | None, typer.Option("--head", "-H", help="Source branch.")] = None,
    reviewer: Annotated[
        list[str] | None, typer.Option("--reviewer", "-r", help="Reviewer account_id or {uuid}.")
    ] = None,
    draft: Annotated[bool, typer.Option("--draft", "-d", help="Create as draft.")] = False,
    fill: Annotated[
        bool, typer.Option("--fill", "-f", help="Title/body from last commit.")
    ] = False,
    no_jira: Annotated[bool, typer.Option("--no-jira", help="Skip Jira link/transition.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print actions; write nothing.")
    ] = False,
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Open a pull request; auto-link and transition the branch's Jira ticket."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> None:
        async with _bb(config) as client:
            source = head or current_branch()
            if not source:
                msg = "No source branch (not on a git branch and no --head)."
                raise BjError(msg)
            key = None if no_jira else parse_branch_key(source, config.branch_key)
            jira = None if no_jira else _jira_if_configured(config)
            final_title, final_body = await _resolve_title_body(
                jira, key, title=title, body=body, source=source, fill=fill
            )
            dest = base
            if not dest:
                repo_obj = await client.get_repo(ref.workspace, ref.repo_slug)
                dest = repo_obj.get("mainbranch", {}).get("name", "main")

            payload: dict[str, Any] = {
                "title": final_title,
                "source": {"branch": {"name": source}},
                "destination": {"branch": {"name": dest}},
                "description": final_body,
                "draft": draft,
            }
            if reviewer:
                payload["reviewers"] = [_reviewer_ref(r) for r in reviewer]

            if dry_run:
                console.print("[bold]Dry run — would create PR:[/bold]")
                console.print(f"  {source} → {dest}\n  title: {final_title}")
                if key and jira:
                    console.print(f"  link + transition {key} → {config.transitions.on_pr_create}")
                    await jira.aclose()
                return

            pr = await client.create_pr(ref.workspace, ref.repo_slug, payload)
            if key and jira:
                url = pr.get("links", {}).get("html", {}).get("href") or ""
                await _apply_jira_on_create(
                    jira, key, config.transitions.on_pr_create, url, final_title
                )
                await jira.aclose()
            if emit(pr, as_json=as_json, jq=jq):
                return
            success(f"Created PR #{pr.get('id')}")
            render_pr(pr)

    run(_run())


@pr_app.command(name="list")
def list_prs(
    state: Annotated[str, typer.Option("--state", "-s", help="open|merged|declined|all.")] = "open",
    head: Annotated[
        str | None, typer.Option("--head", "-H", help="Filter by source branch.")
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", help="Max results.")] = 30,
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
    web: WebOpt = False,
) -> None:
    """List pull requests in a repository."""
    config = load_config()
    ref = resolve_repo(repo)
    if web:
        _open_web(f"https://bitbucket.org/{ref}/pull-requests/")
        return
    state_map = {"open": "OPEN", "merged": "MERGED", "declined": "DECLINED", "closed": "DECLINED"}

    async def _run() -> None:
        async with _bb(config) as client:
            if state == "all":
                query = '(state="OPEN" OR state="MERGED" OR state="DECLINED")'
                prs = await client.list_prs(
                    ref.workspace, ref.repo_slug, source_branch=head, query=query, limit=limit
                )
            else:
                bb_state = state_map.get(state.lower(), state.upper())
                prs = await client.list_prs(
                    ref.workspace, ref.repo_slug, state=bb_state, source_branch=head, limit=limit
                )
            if emit(prs, as_json=as_json, jq=jq):
                return
            render_pr_list(prs)

    run(_run())


@pr_app.command()
def view(
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    comments: Annotated[bool, typer.Option("--comments", "-c", help="Show comments.")] = False,
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
    web: WebOpt = False,
) -> None:
    """View a pull request."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> None:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            pr = await client.get_pr(ref.workspace, ref.repo_slug, resolved)
            if web:
                _open_web(pr.get("links", {}).get("html", {}).get("href"))
                return
            comment_list = (
                await client.list_pr_comments(ref.workspace, ref.repo_slug, resolved)
                if comments
                else None
            )
            if emit(pr, as_json=as_json, jq=jq):
                return
            render_pr(pr, comment_list)

    run(_run())


@pr_app.command()
def diff(
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    stat: Annotated[bool, typer.Option("--stat", help="Show a diffstat summary.")] = False,
    repo: RepoOpt = None,
) -> None:
    """View the changes in a pull request."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> None:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            if stat:
                stats = await client.pr_diffstat(ref.workspace, ref.repo_slug, resolved)
                for entry in stats:
                    path = (entry.get("new") or entry.get("old") or {}).get("path", "?")
                    console.print(f"{entry.get('status', ''):>10}  {path}")
                return
            console.print(await client.pr_diff(ref.workspace, ref.repo_slug, resolved))

    run(_run())


@pr_app.command()
def checkout(
    pr_id: Annotated[int, typer.Argument(help="PR id to check out.")],
    repo: RepoOpt = None,
) -> None:
    """Check out a pull request's source branch locally."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> str:
        async with _bb(config) as client:
            pr = await client.get_pr(ref.workspace, ref.repo_slug, pr_id)
        return str(pr.get("source", {}).get("branch", {}).get("name", ""))

    branch = run(_run())
    if not branch:
        msg = "Could not determine the PR's source branch."
        raise BjError(msg)
    checkout_branch(branch)
    success(f"Checked out {branch}")


@pr_app.command()
def merge(
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    squash: Annotated[bool, typer.Option("--squash", "-s", help="Squash merge.")] = False,
    fast_forward: Annotated[
        bool, typer.Option("--fast-forward", help="Fast-forward merge.")
    ] = False,
    delete_branch: Annotated[
        bool, typer.Option("--delete-branch", "-d", help="Close source branch.")
    ] = False,
    message: Annotated[
        str | None, typer.Option("--message", "-m", help="Merge commit message.")
    ] = None,
    no_jira: Annotated[bool, typer.Option("--no-jira", help="Skip Jira transition.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print actions; write nothing.")
    ] = False,
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Merge a pull request; transition the linked Jira ticket to done."""
    config = load_config()
    ref = resolve_repo(repo)
    strategy = "squash" if squash else "fast_forward" if fast_forward else "merge_commit"

    async def _run() -> None:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            pr = await client.get_pr(ref.workspace, ref.repo_slug, resolved)
            source = pr.get("source", {}).get("branch", {}).get("name", "")
            key = None if no_jira else parse_branch_key(source, config.branch_key)
            if dry_run:
                console.print(f"[bold]Dry run — would merge PR #{resolved} ({strategy})[/bold]")
                if key:
                    console.print(f"  transition {key} → {config.transitions.on_pr_merge}")
                return
            payload: dict[str, Any] = {
                "merge_strategy": strategy,
                "close_source_branch": delete_branch,
            }
            if message:
                payload["message"] = message
            merged = await client.merge_pr(ref.workspace, ref.repo_slug, resolved, payload)
            jira = None if no_jira else _jira_if_configured(config)
            if key and jira:
                target = config.transitions.on_pr_merge
                if target and await transition_to(jira, key, target):
                    console.print(f"[green]✓[/green] {key} → {target}")
                elif target:
                    console.print(f"[yellow]![/yellow] {key}: no '{target}' transition available")
                await jira.aclose()
            if emit(merged, as_json=as_json, jq=jq):
                return
            success(f"Merged PR #{resolved} ({strategy})")

    run(_run())


@pr_app.command()
def review(
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    approve: Annotated[bool, typer.Option("--approve", help="Approve the PR.")] = False,
    request_changes: Annotated[
        bool, typer.Option("--request-changes", help="Request changes.")
    ] = False,
    unapprove: Annotated[bool, typer.Option("--unapprove", help="Remove your approval.")] = False,
    repo: RepoOpt = None,
) -> None:
    """Approve, request changes on, or unapprove a pull request."""
    config = load_config()
    ref = resolve_repo(repo)
    chosen = sum([approve, request_changes, unapprove])
    if chosen != 1:
        msg = "Pass exactly one of --approve, --request-changes, --unapprove."
        raise BjError(msg)

    async def _run() -> None:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            if approve:
                await client.approve_pr(ref.workspace, ref.repo_slug, resolved)
                success(f"Approved PR #{resolved}")
            elif request_changes:
                await client.request_changes_pr(ref.workspace, ref.repo_slug, resolved)
                success(f"Requested changes on PR #{resolved}")
            else:
                await client.unapprove_pr(ref.workspace, ref.repo_slug, resolved)
                success(f"Removed approval on PR #{resolved}")

    run(_run())


@pr_app.command()
def comment(
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="Comment text.")] = None,
    repo: RepoOpt = None,
) -> None:
    """Add a comment to a pull request."""
    config = load_config()
    ref = resolve_repo(repo)
    text = body or typer.prompt("Comment")

    async def _run() -> None:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            await client.add_pr_comment(ref.workspace, ref.repo_slug, resolved, text)
            success(f"Commented on PR #{resolved}")

    run(_run())


@pr_app.command()
def close(
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    repo: RepoOpt = None,
) -> None:
    """Decline (close) a pull request."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> None:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            await client.decline_pr(ref.workspace, ref.repo_slug, resolved)
            success(f"Declined PR #{resolved}")

    run(_run())


@pr_app.command()
def status(
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Show open PRs relevant to you (authored or reviewing)."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> None:
        async with _bb(config) as client:
            me = await client.current_user()
            my_id = me.get("account_id") or me.get("uuid")
            prs = await client.list_prs(ref.workspace, ref.repo_slug, state="OPEN", limit=50)
            mine = []
            for pr in prs:
                author = pr.get("author", {})
                participants = pr.get("participants", []) or []
                reviewer_ids = {p.get("user", {}).get("account_id") for p in participants}
                if author.get("account_id") == my_id or my_id in reviewer_ids:
                    mine.append(pr)
            if emit(mine, as_json=as_json, jq=jq):
                return
            console.print("[bold]Pull requests relevant to you[/bold]")
            render_pr_list(mine)

    run(_run())
