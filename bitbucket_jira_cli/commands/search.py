"""`bj search` - search Bitbucket repositories/code and Jira issues."""

from __future__ import annotations

import re
import webbrowser
from typing import Annotated
from typing import Any
from typing import Literal
from urllib.parse import quote
from urllib.parse import urlparse

import typer
from rich.markup import escape

from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.commands._common import resolve_workspace
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import bitbucket_authorization
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.render import render_issue_list
from bitbucket_jira_cli.render import render_repo_list
from bitbucket_jira_cli.ui import console

search_app = typer.Typer(help="Search Bitbucket and Jira.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
# `-w` is `--web` everywhere else (as in gh), so the workspace uses `-W` like `bj webhook`.
WsOpt = Annotated[
    str | None, typer.Option("--workspace", "-W", help="Workspace (default: configured).")
]
LimitOpt = Annotated[int, typer.Option("--limit", "-L", help="Max results.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


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


def _code_query(
    query: str,
    *,
    repo: str | None,
    language: str | None,
    extension: str | None,
    path: str | None,
) -> str:
    """Append gh-style filter flags to the query as Bitbucket search modifiers."""
    parts = [query]
    if repo:
        parts.append(f"repo:{repo}")
    if language:
        parts.append(f"lang:{language}")
    if extension:
        parts.append(f"ext:{extension.lstrip('.')}")
    if path:
        parts.append(f"path:{path}")
    return " ".join(parts)


def _hit_repo(hit: dict[str, Any]) -> str:
    """Repository full name of a code search hit.

    Falls back to the file's API link when the response has no repository object.
    """
    file_info = hit.get("file", {})
    name = file_info.get("commit", {}).get("repository", {}).get("full_name")
    if name:
        return str(name)
    href = file_info.get("links", {}).get("self", {}).get("href", "")
    match = re.search(r"/repositories/([^/]+)/([^/]+)/", urlparse(href).path)
    return f"{match.group(1)}/{match.group(2)}" if match else ""


def _match_lines(hit: dict[str, Any]) -> list[tuple[int, str]]:
    """The matching lines of a hit as (line number, Rich markup) pairs."""
    lines: list[tuple[int, str]] = []
    for content in hit.get("content_matches", []):
        for line in content.get("lines", []):
            segments = line.get("segments", [])
            if not any(seg.get("match") for seg in segments):
                continue
            text = "".join(
                f"[bold yellow]{escape(seg.get('text', ''))}[/bold yellow]"
                if seg.get("match")
                else escape(seg.get("text", ""))
                for seg in segments
            )
            lines.append((int(line.get("line", 0)), text.strip()))
    return lines


def render_code_hits(results: list[dict[str, Any]]) -> None:
    if not results:
        console.print("[dim]No matches.[/dim]")
        return
    for hit in results:
        repo = _hit_repo(hit)
        path = hit.get("file", {}).get("path", "")
        console.print(f"[cyan]{escape(repo)}[/cyan] {escape(path)}")
        for number, text in _match_lines(hit):
            console.print(f"  [dim]{number}:[/dim] {text}")


@search_app.command()
def code(
    query: Annotated[str, typer.Argument(help="Code search query.")],
    workspace: WsOpt = None,
    repo: Annotated[
        str | None,
        typer.Option("--repo", "-R", help="Restrict to a repository (REPO or WORKSPACE/REPO)."),
    ] = None,
    language: Annotated[
        str | None, typer.Option("--language", help="Restrict to a language (lang:).")
    ] = None,
    extension: Annotated[
        str | None, typer.Option("--extension", help="Restrict to a file extension (ext:).")
    ] = None,
    path: Annotated[
        str | None,
        typer.Option("--path", "--filename", help="Restrict to a path or file name (path:)."),
    ] = None,
    limit: LimitOpt = 30,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Search code across a workspace.

    The filter flags are added to the query as Bitbucket search modifiers, so
    `--language sql` is the same as writing `lang:sql` in the query.
    """
    config = load_config()
    if repo and "/" in repo:
        if repo.count("/") != 1:
            msg = "--repo must be REPO or WORKSPACE/REPO."
            raise BjError(msg)
        repo_ws, repo = repo.split("/", 1)
        workspace = workspace or repo_ws
    ws = resolve_workspace(workspace, config.bitbucket.workspace)
    search_query = _code_query(query, repo=repo, language=language, extension=extension, path=path)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.search_code(ws, search_query, limit=limit)

    results = run_with_status("Searching code…", _run())
    if not emit(results, as_json=as_json, jq=jq):
        render_code_hits(results)


_ORDER_BY = re.compile(r"\s+order\s+by\s+", re.IGNORECASE)


def _quote_jql(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


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
        clauses.append(f"project = {_quote_jql(project)}")
    if issue_type:
        clauses.append(f"issuetype = {_quote_jql(issue_type)}")
    for who, field in ((assignee, "assignee"), (author, "reporter")):
        if who:
            clauses.append(
                f"{field} = currentUser()"
                if who in ("@me", "me")
                else f"{field} = {_quote_jql(who)}"
            )
    if state == "open":
        clauses.append("statusCategory != Done")
    elif state == "closed":
        clauses.append("statusCategory = Done")
    clauses.extend(f"labels = {_quote_jql(label)}" for label in labels or [])
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
