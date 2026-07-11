"""`bj pr` — Bitbucket pull requests, with branch-key Jira automation."""

from __future__ import annotations

import webbrowser
from typing import Annotated
from typing import Any

import questionary
import typer

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
from bitbucket_jira_cli.interaction import checkbox
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import edit_text
from bitbucket_jira_cli.interaction import is_interactive
from bitbucket_jira_cli.interaction import optional_input
from bitbucket_jira_cli.interaction import page
from bitbucket_jira_cli.interaction import require_input
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.interaction import select
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
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]

_MERGE_CHOICES = [
    questionary.Choice("Create a merge commit", value="merge_commit"),
    questionary.Choice("Squash and merge", value="squash"),
    questionary.Choice("Fast-forward", value="fast_forward"),
]


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


# -- create -----------------------------------------------------------------
async def _fetch_create_context(
    config: Config, ref: RepoRef, key: str | None, *, want_members: bool
) -> dict[str, Any]:
    """One network round-trip for the data the compose prompts need."""
    async with _bb(config) as client:
        repo_obj = await client.get_repo(ref.workspace, ref.repo_slug)
        members: list[dict[str, Any]] = []
        if want_members:
            try:
                members = await client.list_workspace_members(ref.workspace)
            except BjError:
                members = []
    summary = ""
    if key:
        jira = _jira_if_configured(config)
        if jira:
            async with jira:
                issue = await jira.get_issue(key, fields=["summary"])
            summary = str(issue.get("fields", {}).get("summary", ""))
    return {
        "default_base": repo_obj.get("mainbranch", {}).get("name", "main"),
        "ticket_summary": summary,
        "members": members,
    }


def _compose_title_body(
    ctx: dict[str, Any],
    key: str | None,
    *,
    title: str | None,
    body: str | None,
    fill: bool,
    editor: bool,
) -> tuple[str, str]:
    final_title = title
    final_body = body or ""
    if fill:
        final_title = final_title or last_commit_subject()
        final_body = final_body or (last_commit_body() or "")
    if not final_title and ctx["ticket_summary"]:
        final_title = f"{key}: {ctx['ticket_summary']}".strip()
    final_title = require_input(final_title or None, flag="--title", label="Title")
    if not final_body:
        final_body = edit_text("") or "" if editor else optional_input("Body (optional)")
    if key and key not in final_body:
        final_body = (final_body + f"\n\nJira: {key}").strip()
    return final_title, final_body


def _choose_reviewers(ctx: dict[str, Any], reviewer: list[str] | None) -> list[dict[str, str]]:
    if reviewer:
        return [_reviewer_ref(r) for r in reviewer]
    if not (is_interactive() and ctx["members"]):
        return []
    choices = [
        questionary.Choice(
            m.get("user", {}).get("display_name", "?"), value=m.get("user", {}).get("account_id")
        )
        for m in ctx["members"]
        if m.get("user", {}).get("account_id")
    ]
    if not choices:
        return []
    picked = checkbox("Reviewers (space to select, enter to confirm)", choices)
    return [{"account_id": a} for a in picked if a]


async def _do_create(
    config: Config, ref: RepoRef, payload: dict[str, Any], key: str | None, title: str
) -> dict[str, Any]:
    async with _bb(config) as client:
        pr = await client.create_pr(ref.workspace, ref.repo_slug, payload)
    if key:
        jira = _jira_if_configured(config)
        if jira:
            async with jira:
                url = pr.get("links", {}).get("html", {}).get("href") or ""
                await link_pr(jira, key, url, title)
                target = config.transitions.on_pr_create
                if target and await transition_to(jira, key, target):
                    console.print(f"[green]✓[/green] {key} → {target}")
                elif target:
                    console.print(f"[yellow]![/yellow] {key}: no '{target}' transition available")
    return pr


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
    editor: Annotated[
        bool, typer.Option("--editor", "-e", help="Write the body in $EDITOR.")
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
    source = head or current_branch()
    if not source:
        msg = "No source branch (not on a git branch and no --head)."
        raise BjError(msg)
    key = None if no_jira else parse_branch_key(source, config.branch_key)

    want_members = is_interactive() and not reviewer and not draft
    ctx = run_with_status(
        "Loading…", _fetch_create_context(config, ref, key, want_members=want_members)
    )
    final_title, final_body = _compose_title_body(
        ctx, key, title=title, body=body, fill=fill, editor=editor
    )
    dest = base or ctx["default_base"]
    reviewers = _choose_reviewers(ctx, reviewer)

    payload: dict[str, Any] = {
        "title": final_title,
        "source": {"branch": {"name": source}},
        "destination": {"branch": {"name": dest}},
        "description": final_body,
        "draft": draft,
    }
    if reviewers:
        payload["reviewers"] = reviewers

    if dry_run:
        console.print("[bold]Dry run — would create PR:[/bold]")
        console.print(f"  {source} → {dest}\n  title: {final_title}")
        if key:
            console.print(f"  link + transition {key} → {config.transitions.on_pr_create}")
        return

    if is_interactive() and not draft:
        action = select(
            "What's next?",
            [
                questionary.Choice("Submit", value="submit"),
                questionary.Choice("Submit as draft", value="draft"),
                questionary.Choice("Open in the browser", value="web"),
                questionary.Choice("Cancel", value="cancel"),
            ],
        )
        if action == "cancel":
            raise typer.Abort
        if action == "web":
            _open_web(f"https://bitbucket.org/{ref}/pull-requests/new?source={source}&dest={dest}")
            return
        payload["draft"] = action == "draft"

    pr = run_with_status(
        "Creating pull request…", _do_create(config, ref, payload, key, final_title)
    )
    if emit(pr, as_json=as_json, jq=jq):
        return
    success(f"Created PR #{pr.get('id')}")
    render_pr(pr)


# -- list / view / diff / status --------------------------------------------
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

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            if state == "all":
                query = '(state="OPEN" OR state="MERGED" OR state="DECLINED")'
                return await client.list_prs(
                    ref.workspace, ref.repo_slug, source_branch=head, query=query, limit=limit
                )
            bb_state = state_map.get(state.lower(), state.upper())
            return await client.list_prs(
                ref.workspace, ref.repo_slug, state=bb_state, source_branch=head, limit=limit
            )

    prs = run_with_status("Loading pull requests…", _run())
    if not emit(prs, as_json=as_json, jq=jq):
        render_pr_list(prs)


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

    async def _run() -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            pr = await client.get_pr(ref.workspace, ref.repo_slug, resolved)
            comment_list = (
                await client.list_pr_comments(ref.workspace, ref.repo_slug, resolved)
                if comments
                else None
            )
            return pr, comment_list

    pr, comment_list = run_with_status("Loading pull request…", _run())
    if web:
        _open_web(pr.get("links", {}).get("html", {}).get("href"))
        return
    if not emit(pr, as_json=as_json, jq=jq):
        render_pr(pr, comment_list)


@pr_app.command()
def diff(
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    stat: Annotated[bool, typer.Option("--stat", help="Show a diffstat summary.")] = False,
    repo: RepoOpt = None,
) -> None:
    """View the changes in a pull request."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> Any:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            if stat:
                return await client.pr_diffstat(ref.workspace, ref.repo_slug, resolved)
            return await client.pr_diff(ref.workspace, ref.repo_slug, resolved)

    result = run_with_status("Loading diff…", _run())
    if stat:
        lines = [
            f"{entry.get('status', ''):>10}  "
            f"{(entry.get('new') or entry.get('old') or {}).get('path', '?')}"
            for entry in result
        ]
        page("\n".join(lines))
    else:
        page(result)


@pr_app.command()
def status(repo: RepoOpt = None, as_json: JsonOpt = False, jq: JqOpt = None) -> None:
    """Show open PRs relevant to you (authored or reviewing)."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            me = await client.current_user()
            my_id = me.get("account_id") or me.get("uuid")
            prs = await client.list_prs(ref.workspace, ref.repo_slug, state="OPEN", limit=50)
            return [
                pr
                for pr in prs
                if pr.get("author", {}).get("account_id") == my_id
                or my_id
                in {p.get("user", {}).get("account_id") for p in pr.get("participants", [])}
            ]

    mine = run_with_status("Loading pull requests…", _run())
    if not emit(mine, as_json=as_json, jq=jq):
        console.print("[bold]Pull requests relevant to you[/bold]")
        render_pr_list(mine)


# -- checkout ---------------------------------------------------------------
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

    branch = run_with_status("Loading pull request…", _run())
    if not branch:
        msg = "Could not determine the PR's source branch."
        raise BjError(msg)
    checkout_branch(branch)
    success(f"Checked out {branch}")


# -- merge ------------------------------------------------------------------
def _explicit_strategy(*, squash: bool, fast_forward: bool, merge: bool) -> str | None:
    if squash:
        return "squash"
    if fast_forward:
        return "fast_forward"
    if merge:
        return "merge_commit"
    return None


def _prompt_merge_method(delete_branch: bool) -> tuple[str, bool]:
    if not is_interactive():
        msg = (
            "a merge method (--merge, --squash, or --fast-forward) is required "
            "when not running interactively"
        )
        raise BjError(msg)
    strategy = select("What merge method would you like to use?", _MERGE_CHOICES)
    if strategy != "fast_forward" and not delete_branch:
        delete_branch = confirm("Delete the source branch after merge?", yes=False)
    return strategy, delete_branch


async def _transition_after_merge(config: Config, key: str) -> None:
    jira = _jira_if_configured(config)
    if not jira:
        return
    async with jira:
        target = config.transitions.on_pr_merge
        if target and await transition_to(jira, key, target):
            console.print(f"[green]✓[/green] {key} → {target}")
        elif target:
            console.print(f"[yellow]![/yellow] {key}: no '{target}' transition")


@pr_app.command()
def merge(  # noqa: PLR0913 — mirrors `gh pr merge`.
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    merge_commit: Annotated[bool, typer.Option("--merge", help="Merge commit.")] = False,
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
    yes: YesOpt = False,
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

    async def _fetch() -> tuple[int, str]:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            pr = await client.get_pr(ref.workspace, ref.repo_slug, resolved)
        return resolved, pr.get("source", {}).get("branch", {}).get("name", "")

    resolved, source = run_with_status("Loading pull request…", _fetch())
    key = None if no_jira else parse_branch_key(source, config.branch_key)

    strategy = _explicit_strategy(squash=squash, fast_forward=fast_forward, merge=merge_commit)
    if strategy is None:
        strategy, delete_branch = _prompt_merge_method(delete_branch)

    if dry_run:
        console.print(f"[bold]Dry run — would merge PR #{resolved} ({strategy})[/bold]")
        if key:
            console.print(f"  transition {key} → {config.transitions.on_pr_merge}")
        return
    if not confirm(f"Merge pull request #{resolved} ({strategy})?", yes=yes, default=True):
        raise typer.Abort

    payload: dict[str, Any] = {"merge_strategy": strategy, "close_source_branch": delete_branch}
    if message:
        payload["message"] = message

    async def _merge() -> dict[str, Any]:
        async with _bb(config) as client:
            merged = await client.merge_pr(ref.workspace, ref.repo_slug, resolved, payload)
        if key:
            await _transition_after_merge(config, key)
        return merged

    merged = run_with_status("Merging…", _merge())
    if not emit(merged, as_json=as_json, jq=jq):
        success(f"Merged PR #{resolved} ({strategy})")


# -- review / comment / close ------------------------------------------------
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
    if sum([approve, request_changes, unapprove]) != 1:
        msg = "Pass exactly one of --approve, --request-changes, --unapprove."
        raise BjError(msg)

    async def _run() -> int:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            if approve:
                await client.approve_pr(ref.workspace, ref.repo_slug, resolved)
            elif request_changes:
                await client.request_changes_pr(ref.workspace, ref.repo_slug, resolved)
            else:
                await client.unapprove_pr(ref.workspace, ref.repo_slug, resolved)
            return resolved

    resolved = run_with_status("Submitting review…", _run())
    verb = "Approved" if approve else "Requested changes on" if request_changes else "Unapproved"
    success(f"{verb} PR #{resolved}")


@pr_app.command()
def comment(
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    body: Annotated[str | None, typer.Option("--body", "-b", help="Comment text.")] = None,
    editor: Annotated[
        bool, typer.Option("--editor", "-e", help="Write the comment in $EDITOR.")
    ] = False,
    repo: RepoOpt = None,
) -> None:
    """Add a comment to a pull request."""
    config = load_config()
    ref = resolve_repo(repo)
    text = require_input(body, flag="--body", label="Comment", editor=editor)

    async def _run() -> int:
        async with _bb(config) as client:
            resolved = await _resolve_id(client, ref, pr_id)
            await client.add_pr_comment(ref.workspace, ref.repo_slug, resolved, text)
            return resolved

    resolved = run_with_status("Adding comment…", _run())
    success(f"Commented on PR #{resolved}")


@pr_app.command()
def close(
    pr_id: Annotated[int | None, typer.Argument(help="PR id (default: current branch).")] = None,
    yes: YesOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Decline (close) a pull request."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _fetch() -> int:
        async with _bb(config) as client:
            return await _resolve_id(client, ref, pr_id)

    resolved = run_with_status("Loading pull request…", _fetch())
    if not confirm(f"Decline pull request #{resolved}?", yes=yes):
        raise typer.Abort

    async def _close() -> None:
        async with _bb(config) as client:
            await client.decline_pr(ref.workspace, ref.repo_slug, resolved)

    run_with_status("Declining…", _close())
    success(f"Declined PR #{resolved}")
