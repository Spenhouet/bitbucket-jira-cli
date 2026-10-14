"""`bj issue attachment` - list and download Jira issue attachments."""

from __future__ import annotations

import contextlib
import fnmatch
import sys
from pathlib import Path
from typing import Annotated
from typing import Any

import typer
from rich.table import Table

from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.commands.issue import JqOpt
from bitbucket_jira_cli.commands.issue import JsonOpt
from bitbucket_jira_cli.commands.issue import _resolve_key
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.timefmt import relative_time
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import err_console
from bitbucket_jira_cli.ui import success

attachment_app = typer.Typer(help="List and download issue attachments.", no_args_is_help=True)

KeyArg = Annotated[str | None, typer.Argument(help="Issue key (default: from branch).")]

_KIB = 1024


def human_size(size: int) -> str:
    """Byte count as a short human string: 512 B, 1.5 KiB, 2.0 MiB."""
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < _KIB or unit == "GiB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= _KIB
    return f"{size} B"


def _render_attachments(key: str, attachments: list[dict[str, Any]]) -> None:
    if not attachments:
        console.print(f"[dim]No attachments on {key}.[/dim]")
        return
    table = Table(box=None, pad_edge=False)
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name")
    table.add_column("Size", justify="right")
    table.add_column("Type", style="dim")
    table.add_column("Created", style="dim")
    for item in attachments:
        table.add_row(
            str(item.get("id", "")),
            str(item.get("filename", "")),
            human_size(int(item.get("size") or 0)),
            str(item.get("mimeType", "")),
            relative_time(item.get("created")),
        )
    console.print(table)


async def _load(key: str) -> list[dict[str, Any]]:
    async with jira_client(load_config()) as client:
        return await client.list_attachments(key)


@attachment_app.command(name="list")
def list_attachments(key: KeyArg = None, as_json: JsonOpt = False, jq: JqOpt = None) -> None:
    """List the attachments on an issue."""
    resolved = _resolve_key(key, load_config())
    attachments = run_with_status("Loading attachments…", _load(resolved))
    if not emit(attachments, as_json=as_json, jq=jq):
        _render_attachments(resolved, attachments)


def select_attachments(
    attachments: list[dict[str, Any]],
    *,
    names: list[str],
    patterns: list[str],
    ids: list[str],
) -> list[dict[str, Any]]:
    """Attachments matching any given name, glob pattern or id (all when none given)."""
    if not (names or patterns or ids):
        return list(attachments)
    selected = []
    for item in attachments:
        filename = str(item.get("filename", ""))
        if (
            filename in names
            or str(item.get("id", "")) in ids
            or any(fnmatch.fnmatchcase(filename, pattern) for pattern in patterns)
        ):
            selected.append(item)
    return selected


def safe_filename(filename: str) -> str:
    """The file name to write locally, without any directory part."""
    name = Path(filename.replace("\\", "/")).name
    if name in {"", ".", ".."}:
        msg = f"Attachment name '{filename}' is not a valid file name. Use --output instead."
        raise BjError(msg)
    return name


def _plan_targets(
    selected: list[dict[str, Any]], directory: Path, *, clobber: bool, skip_existing: bool
) -> list[tuple[dict[str, Any], Path]]:
    """Pair each attachment with its target path, checking for name clashes."""
    seen: dict[str, str] = {}
    targets = []
    for item in selected:
        name = safe_filename(str(item.get("filename", "")))
        if name in seen:
            msg = (
                f"Several attachments are named '{name}' (ids {seen[name]} and "
                f"{item.get('id')}). Pick one with --id and --output."
            )
            raise BjError(msg)
        seen[name] = str(item.get("id"))
        path = directory / name
        if path.exists() and not clobber:
            if skip_existing:
                continue
            msg = f"{path} already exists (use --clobber to overwrite or --skip-existing)."
            raise BjError(msg)
        targets.append((item, path))
    return targets


async def _download_to_files(targets: list[tuple[dict[str, Any], Path]]) -> None:
    async with jira_client(load_config()) as client:
        for item, path in targets:
            part = path.with_name(path.name + ".part")
            try:
                with part.open("wb") as sink:
                    await client.download_attachment(str(item.get("id")), sink)
                part.replace(path)
            finally:
                with contextlib.suppress(FileNotFoundError):
                    part.unlink()


async def _download_to_stdout(item: dict[str, Any]) -> None:
    async with jira_client(load_config()) as client:
        await client.download_attachment(str(item.get("id")), sys.stdout.buffer)
    sys.stdout.buffer.flush()


@attachment_app.command()
def download(
    key: KeyArg = None,
    name: Annotated[
        list[str] | None,
        typer.Option("--name", "-n", help="Download attachments with this file name (repeatable)."),
    ] = None,
    pattern: Annotated[
        list[str] | None,
        typer.Option("--pattern", "-p", help="Download attachments matching a glob (repeatable)."),
    ] = None,
    attachment_id: Annotated[
        list[str] | None,
        typer.Option("--id", help="Download the attachment with this id (repeatable)."),
    ] = None,
    directory: Annotated[
        Path, typer.Option("--dir", "-D", help="Directory to download files into.")
    ] = Path(),
    output: Annotated[
        str | None,
        typer.Option(
            "--output", "-O", help="File to write a single attachment to ('-' for stdout)."
        ),
    ] = None,
    clobber: Annotated[
        bool, typer.Option("--clobber", help="Overwrite existing files of the same name.")
    ] = False,
    skip_existing: Annotated[
        bool, typer.Option("--skip-existing", help="Skip files that already exist.")
    ] = False,
) -> None:
    """Download issue attachments (all of them unless filtered)."""
    if clobber and skip_existing:
        msg = "--clobber and --skip-existing cannot be used together."
        raise BjError(msg)
    resolved = _resolve_key(key, load_config())
    attachments = run_with_status("Loading attachments…", _load(resolved))
    selected = select_attachments(
        attachments, names=name or [], patterns=pattern or [], ids=attachment_id or []
    )
    if not selected:
        what = "attachments" if not (name or pattern or attachment_id) else "matching attachments"
        msg = f"No {what} on {resolved}. See `bj issue attachment list {resolved}`."
        raise BjError(msg)

    if output is not None:
        if len(selected) > 1:
            msg = (
                f"--output takes a single attachment, but {len(selected)} match. "
                "Narrow it down with --name, --pattern or --id."
            )
            raise BjError(msg)
        if output == "-":
            run_with_status("Downloading…", _download_to_stdout(selected[0]))
            return
        out_path = Path(output)
        targets = _plan_targets(
            [{**selected[0], "filename": out_path.name}],
            out_path.parent,
            clobber=clobber,
            skip_existing=skip_existing,
        )
    else:
        directory.mkdir(parents=True, exist_ok=True)
        targets = _plan_targets(selected, directory, clobber=clobber, skip_existing=skip_existing)

    if targets:
        run_with_status("Downloading…", _download_to_files(targets))
    for _, path in targets:
        success(f"Downloaded {path}")
    skipped = len(selected) - len(targets)
    if skipped:
        err_console.print(f"[dim]Skipped {skipped} existing file(s).[/dim]")
