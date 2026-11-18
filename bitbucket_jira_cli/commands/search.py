"""`bj search` - search Bitbucket repositories, code, pull requests, commits and Jira issues."""

from __future__ import annotations

import asyncio
import re
import webbrowser
from datetime import date
from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Literal
from urllib.parse import quote

import typer
from rich.markup import escape

from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.commands._common import resolve_repo
from bitbucket_jira_cli.commands._common import resolve_workspace
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import bitbucket_authorization
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.errors import ApiError
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.render import render_commit_list
from bitbucket_jira_cli.render import render_issue_list
from bitbucket_jira_cli.render import render_pr_search_list
from bitbucket_jira_cli.render import render_repo_list
from bitbucket_jira_cli.ui import console

HTTP_FORBIDDEN = 403

search_app = typer.Typer(help="Search Bitbucket and Jira.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
# `-w` is `--web` everywhere else (as in gh), so the workspace uses `-W` like `bj webhook`.
WsOpt = Annotated[
    str | None, typer.Option("--workspace", "-W", help="Workspace (default: configured).")
]
LimitOpt = Annotated[int, typer.Option("--limit", "-L", help="Max results.")]
RepoOpt = Annotated[
    str | None,
    typer.Option("--repo", "-R", help="Restrict to a repository (REPO or WORKSPACE/REPO)."),
]
# Requests in flight at once when a search fans out over every repository.
_FAN_OUT = 8


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


def _quoted(value: str) -> str:
    """A double-quoted string literal for JQL or Bitbucket's BBQL."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _split_repo(repo: str | None, workspace: str | None) -> tuple[str | None, str | None]:
    """Split ``--repo`` (REPO or WORKSPACE/REPO) into (workspace, repo slug)."""
    if not repo or "/" not in repo:
        return workspace, repo
    if repo.count("/") != 1:
        msg = "--repo must be REPO or WORKSPACE/REPO."
        raise BjError(msg)
    repo_ws, slug = repo.split("/", 1)
    return workspace or repo_ws, slug


@search_app.command()
def repos(
    query: Annotated[str, typer.Argument(help="Text to match in repository names.")],
    workspace: WsOpt = None,
    limit: LimitOpt = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search repositories in a workspace by name."""
    config = load_config()
    ws = resolve_workspace(workspace, config.bitbucket.workspace)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.list_repos(ws, query=f'name~"{query}"', limit=limit)

    results = run_with_status("Searching…", _run())
    if not emit(results, as_json=as_json, jq=jq):
        render_repo_list(results)


# Query modifiers of the old code search, still accepted in the query.
_CODE_MODIFIERS = {"repo": "repository", "lang": "language", "ext": "extension", "path": "path"}
# Attributes that take a `*`/`?` pattern; the others only match a value.
_WILDCARD_ATTRIBUTES = ("repository", "path")


def _code_filter(attribute: str, value: str) -> dict[str, str]:
    """One code search filter; a `*` or `?` makes a repository or path filter a pattern."""
    if attribute == "extension":
        value = value.lstrip(".")
    pattern = attribute in _WILDCARD_ATTRIBUTES and any(char in value for char in "*?")
    return {"attribute": attribute, "wildcard" if pattern else "eq": value}


def _code_query(
    query: str,
    *,
    repo: str | None,
    language: str | None,
    extension: str | None,
    path: str | None,
) -> tuple[str, dict[str, Any] | None]:
    """Search term and filters for the code search.

    The filter flags and the `repo:`, `lang:`, `ext:` and `path:` modifiers in the
    query become filters. The rest of the query is the search term.
    """
    words: list[str] = []
    filters: list[dict[str, str]] = []
    for word in query.split():
        key, colon, value = word.partition(":")
        if colon and value and key in _CODE_MODIFIERS:
            filters.append(_code_filter(_CODE_MODIFIERS[key], value))
        else:
            words.append(word)
    flags = (("repository", repo), ("language", language), ("extension", extension), ("path", path))
    filters.extend(_code_filter(attribute, value) for attribute, value in flags if value)
    term = " ".join(words)
    if not term:
        msg = "The query needs a search term next to the filters."
        raise BjError(msg)
    if not filters:
        return term, None
    return term, filters[0] if len(filters) == 1 else {"and": filters}


def _hit_repo(hit: dict[str, Any]) -> str:
    """Repository of a code search hit as WORKSPACE/REPO."""
    repo = hit.get("repository") or {}
    ns, name = repo.get("ns"), repo.get("name")
    return f"{ns}/{name}" if ns and name else str(name or "")


def _highlight(text: str, ranges: list[tuple[int, int]]) -> str:
    """Rich markup of a line with the given column ranges in bold yellow."""
    parts: list[str] = []
    position = 0
    for start, end in sorted(ranges):
        if start < position:
            continue
        parts.append(escape(text[position:start]))
        parts.append(f"[bold yellow]{escape(text[start:end])}[/bold yellow]")
        position = end
    parts.append(escape(text[position:]))
    return "".join(parts)


def _match_lines(hit: dict[str, Any], term: str) -> list[tuple[int, str]]:
    """The matching lines of a hit as (line number, Rich markup) pairs.

    Bitbucket marks only whole-word matches, so a line that contains the term
    without a mark is shown as well.
    """
    lines: list[tuple[int, str]] = []
    needle = term.lower()
    for chunk in hit.get("matched_chunks") or []:
        first = int((chunk.get("line_range") or {}).get("start", 1))
        ranges: dict[int, list[tuple[int, int]]] = {}
        for line, start, end in chunk.get("matched_ranges") or []:
            ranges.setdefault(int(line), []).append((int(start), int(end)))
        marked = {int(n) for n in chunk.get("matched_line_numbers") or []} | set(ranges)
        for offset, text in enumerate(str(chunk.get("source_code", "")).splitlines()):
            number = first + offset
            if number in marked or needle in text.lower():
                lines.append((number, _highlight(text, ranges.get(number, [])).strip()))
    return lines


def render_code_hits(results: list[dict[str, Any]], term: str) -> None:
    if not results:
        console.print("[dim]No matches.[/dim]")
        return
    for hit in results:
        console.print(f"[cyan]{escape(_hit_repo(hit))}[/cyan] {escape(str(hit.get('path', '')))}")
        for number, text in _match_lines(hit, term):
            console.print(f"  [dim]{number}:[/dim] {text}")


@search_app.command()
def code(
    query: Annotated[str, typer.Argument(help="Code search query.")],
    workspace: WsOpt = None,
    repo: RepoOpt = None,
    language: Annotated[
        str | None, typer.Option("--language", help="Restrict to a language, such as python.")
    ] = None,
    extension: Annotated[
        str | None, typer.Option("--extension", help="Restrict to a file extension, such as py.")
    ] = None,
    path: Annotated[
        str | None,
        typer.Option(
            "--path",
            "--filename",
            help="Restrict to a path: folder or file names in order, or a pattern with * and ?.",
        ),
    ] = None,
    limit: LimitOpt = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search code across a workspace.

    Searches the default branch of every repository you can read. The filter
    flags narrow the search; `repo:`, `lang:`, `ext:` and `path:` in the query
    work the same. `--repo` and `--path` take patterns with `*` and `?`.

    Needs an API token or access token: Bitbucket rejects app passwords for
    code search.
    """
    config = load_config()
    workspace, repo = _split_repo(repo, workspace)
    ws = resolve_workspace(workspace, config.bitbucket.workspace)
    term, filters = _code_query(query, repo=repo, language=language, extension=extension, path=path)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.search_code(ws, term, filters=filters, limit=limit)

    try:
        results = run_with_status("Searching code…", _run())
    except ApiError as exc:
        if exc.status != HTTP_FORBIDDEN:
            raise
        msg = (
            f"{exc}. Code search needs an API token with the scopes "
            "read:repository:bitbucket and read:workspace:bitbucket, or an access token. "
            "Bitbucket rejects app passwords for it."
        )
        raise BjError(msg) from exc
    if not emit(results, as_json=as_json, jq=jq):
        render_code_hits(results, term)


# -- pull requests ----------------------------------------------------------
PrState = Literal["open", "merged", "declined", "superseded", "all"]


def _prs_bbql(
    query: str | None,
    *,
    state: PrState,
    author: str | None,
    base: str | None,
    head: str | None,
) -> str:
    """Build the BBQL filter for a pull request search."""
    clauses: list[str] = []
    if query:
        text = _quoted(query)
        clauses.append(f"(title ~ {text} OR description ~ {text})")
    if state == "all":
        states = ("OPEN", "MERGED", "DECLINED", "SUPERSEDED")
        clauses.append("(" + " OR ".join(f'state = "{st}"' for st in states) + ")")
    else:
        clauses.append(f'state = "{state.upper()}"')
    if author:
        field = "author.uuid" if author.startswith("{") else "author.account_id"
        clauses.append(f"{field} = {_quoted(author)}")
    if base:
        clauses.append(f"destination.branch.name = {_quoted(base)}")
    if head:
        clauses.append(f"source.branch.name = {_quoted(head)}")
    return " AND ".join(clauses)


async def _search_prs(
    client: BitbucketClient,
    workspace: str,
    *,
    query: str | None,
    state: PrState,
    author: str | None,
    repo: str | None,
    base: str | None,
    head: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    if author in ("@me", "me"):
        author = str((await client.current_user()).get("uuid", ""))
    sort = "-updated_on"
    if author and not repo:
        # One call covers every repository when the author is known.
        bbql = _prs_bbql(query, state=state, author=None, base=base, head=head)
        return await client.list_user_prs(workspace, author, query=bbql, sort=sort, limit=limit)
    bbql = _prs_bbql(query, state=state, author=author, base=base, head=head)
    if repo:
        return await client.list_prs(workspace, repo, query=bbql, sort=sort, limit=limit)
    # No workspace-wide endpoint without an author: query each repository.
    repos = await client.list_repos(workspace, limit=10_000)
    gate = asyncio.Semaphore(_FAN_OUT)

    async def one(slug: str) -> list[dict[str, Any]]:
        async with gate:
            return await client.list_prs(workspace, slug, query=bbql, sort=sort, limit=limit)

    batches = await asyncio.gather(*(one(str(r.get("slug", ""))) for r in repos))
    found = [pr for batch in batches for pr in batch]
    found.sort(key=lambda pr: str(pr.get("updated_on", "")), reverse=True)
    return found[:limit]


@search_app.command()
def prs(
    query: Annotated[
        str | None, typer.Argument(help="Text to match in the title or description.")
    ] = None,
    workspace: WsOpt = None,
    repo: RepoOpt = None,
    author: Annotated[
        str | None,
        typer.Option("--author", help="Filter by author (@me, account ID or {UUID})."),
    ] = None,
    state: Annotated[PrState, typer.Option("--state", "-s", help="Filter by state.")] = "all",
    base: Annotated[
        str | None, typer.Option("--base", "-B", help="Filter by destination branch.")
    ] = None,
    head: Annotated[
        str | None, typer.Option("--head", "-H", help="Filter by source branch.")
    ] = None,
    limit: LimitOpt = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search pull requests across a workspace.

    With --author this is a single request. Without it, Bitbucket has no
    workspace-wide endpoint, so every repository is queried, which takes longer
    in large workspaces. Narrow it with --repo when you can.
    """
    config = load_config()
    workspace, repo = _split_repo(repo, workspace)
    ws = resolve_workspace(workspace, config.bitbucket.workspace)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await _search_prs(
                client,
                ws,
                query=query,
                state=state,
                author=author,
                repo=repo,
                base=base,
                head=head,
                limit=limit,
            )

    results = run_with_status("Searching pull requests…", _run())
    if not emit(results, as_json=as_json, jq=jq):
        render_pr_search_list(results)


# -- commits ----------------------------------------------------------------
def _commit_matches(
    commit: dict[str, Any], *, query: str | None, author: str | None, me: str | None
) -> bool:
    if query and query.lower() not in str(commit.get("message", "")).lower():
        return False
    if not author:
        return True
    info = commit.get("author", {})
    user = info.get("user", {})
    if me:
        return user.get("uuid") == me
    needle = author.lower()
    fields = (info.get("raw"), user.get("display_name"), user.get("nickname"))
    ids = (user.get("uuid"), user.get("account_id"))
    return any(needle in str(f or "").lower() for f in fields) or author in ids


def _commit_date(commit: dict[str, Any]) -> date | None:
    try:
        return datetime.fromisoformat(str(commit.get("date", ""))).date()
    except ValueError:
        return None


@search_app.command()
def commits(
    query: Annotated[
        str | None, typer.Argument(help="Text to match in the commit message.")
    ] = None,
    repo: Annotated[
        str | None,
        typer.Option("--repo", "-R", help="WORKSPACE/REPO or REPO (default: current repo)."),
    ] = None,
    workspace: WsOpt = None,
    author: Annotated[
        str | None,
        typer.Option("--author", help="Filter by author (@me, name, email or account ID)."),
    ] = None,
    branch: Annotated[
        str | None, typer.Option("--branch", "-b", help="Branch or ref to search.")
    ] = None,
    since: Annotated[
        datetime | None,
        typer.Option("--since", help="Stop at commits older than this date.", formats=["%Y-%m-%d"]),
    ] = None,
    limit: LimitOpt = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search commit messages in one repository.

    Bitbucket cannot filter commits on the server, so bj reads the history
    newest first and matches it locally. Use --since to bound the scan of a
    long history.
    """
    config = load_config()
    if repo and "/" not in repo:
        ref_ws, slug = resolve_workspace(workspace, config.bitbucket.workspace), repo
    else:
        ref = resolve_repo(repo)
        ref_ws, slug = ref.workspace, ref.repo_slug
    cutoff = since.date() if since else None

    async def _run() -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        async with _bb(config) as client:
            me = None
            if author in ("@me", "me"):
                me = str((await client.current_user()).get("uuid", ""))
            async for commit in client.iter_commits(ref_ws, slug, revision=branch):
                day = _commit_date(commit)
                if cutoff and day and day < cutoff:
                    break
                if _commit_matches(commit, query=query, author=author, me=me):
                    found.append(commit)
                    if len(found) >= limit:
                        break
        return found

    results = run_with_status("Searching commits…", _run())
    if not emit(results, as_json=as_json, jq=jq):
        render_commit_list(results)


_ORDER_BY = re.compile(r"\s+order\s+by\s+", re.IGNORECASE)


def _split_order_by(jql: str | None) -> tuple[str, str]:
    """Split a JQL query into its filter and its ORDER BY clause (with a default)."""
    parts = _ORDER_BY.split((jql or "").strip(), maxsplit=1)
    order = f"ORDER BY {parts[1].strip()}" if len(parts) > 1 else "ORDER BY updated DESC"
    return parts[0].strip(), order


def _issues_jql(
    jql: str | None,
    *,
    assignee: str | None,
    author: str | None,
    state: Literal["open", "closed"] | None,
    project: str | None,
    issue_type: str | None,
    labels: list[str] | None,
) -> str:
    """Combine an optional JQL query with gh-style filter flags into one query."""
    where, order = _split_order_by(jql)
    clauses = [f"({where})"] if where else []
    if project:
        clauses.append(f"project = {_quoted(project)}")
    if issue_type:
        clauses.append(f"issuetype = {_quoted(issue_type)}")
    for who, field in ((assignee, "assignee"), (author, "reporter")):
        if who:
            clauses.append(
                f"{field} = currentUser()" if who in ("@me", "me") else f"{field} = {_quoted(who)}"
            )
    if state == "open":
        clauses.append("statusCategory != Done")
    elif state == "closed":
        clauses.append("statusCategory = Done")
    clauses.extend(f"labels = {_quoted(label)}" for label in labels or [])
    if not clauses:
        # `/search/jql` rejects unbounded queries.
        msg = "Give a JQL query or at least one filter flag (e.g. --assignee @me)."
        raise BjError(msg)
    return f"{' AND '.join(clauses)} {order}"


@search_app.command()
def issues(  # noqa: PLR0913 - mirrors the filter flags of `gh search issues`.
    jql: Annotated[str | None, typer.Argument(help="JQL query (optional with filters).")] = None,
    assignee: Annotated[
        str | None, typer.Option("--assignee", help="Filter by assignee (accountId or @me).")
    ] = None,
    author: Annotated[
        str | None, typer.Option("--author", help="Filter by reporter (accountId or @me).")
    ] = None,
    state: Annotated[
        Literal["open", "closed"] | None,
        typer.Option("--state", "-s", help="Filter by state (Jira status category)."),
    ] = None,
    project: Annotated[
        str | None, typer.Option("--project", "-p", help="Filter by project key.")
    ] = None,
    issue_type: Annotated[
        str | None, typer.Option("--type", "-t", help="Filter by issue type.")
    ] = None,
    label: Annotated[
        list[str] | None, typer.Option("--label", "-l", help="Filter by label (repeatable).")
    ] = None,
    web: Annotated[
        bool, typer.Option("--web", "-w", help="Open the search in the browser.")
    ] = False,
    limit: LimitOpt = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search Jira issues with JQL and/or gh-style filter flags.

    Filter flags are joined to the JQL query with AND.
    """
    config = load_config()
    query = _issues_jql(
        jql,
        assignee=assignee,
        author=author,
        state=state,
        project=project,
        issue_type=issue_type,
        labels=label,
    )
    if web:
        site = (config.jira.site or "").rstrip("/")
        if not site:
            msg = "Jira site not configured. Run `bj auth login`."
            raise BjError(msg)
        url = f"{site}/issues/?jql={quote(query)}"
        webbrowser.open(url)
        console.print(f"[dim]Opening {url}[/dim]")
        return

    async def _run() -> list[dict[str, Any]]:
        async with jira_client(config) as client:
            return await client.search(query, limit=limit)

    results = run_with_status("Searching issues…", _run())
    if not emit(results, as_json=as_json, jq=jq):
        render_issue_list(results)
