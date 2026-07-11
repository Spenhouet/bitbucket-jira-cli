"""Interactive prompts and terminal helpers, gh-style.

Everything here is TTY-aware: in an interactive terminal you get arrow-key
selects, confirmations, an editor and a spinner; when piped or when
``BJ_PROMPT_DISABLED`` is set, prompts are skipped and commands must be driven
by flags (or they raise a clear "not running interactively" error).
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeVar

import questionary
import typer

from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.ui import console

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from collections.abc import Sequence

T = TypeVar("T")


def is_interactive() -> bool:
    """True when we may prompt: both stdio are TTYs and prompting is enabled."""
    if os.environ.get("BJ_PROMPT_DISABLED"):
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()


def _answer(question: Any) -> Any:
    value = question.ask()
    if value is None:  # Ctrl-C / EOF
        raise typer.Abort
    return value


def require_input(value: str | None, *, flag: str, label: str, editor: bool = False) -> str:
    """Return ``value``, else prompt (editor or text) when interactive, else error."""
    if value is not None:
        return value
    if editor:
        edited = edit_text("")
        if edited is not None and edited.strip():
            return edited
    if is_interactive():
        return str(_answer(questionary.text(label))).strip()
    msg = f"must provide {flag} when not running interactively"
    raise BjError(msg)


def optional_input(label: str, *, default: str = "") -> str:
    if not is_interactive():
        return default
    return str(_answer(questionary.text(label, default=default))).strip()


def select(message: str, choices: Sequence[Any], *, default: Any = None) -> Any:
    return _answer(questionary.select(message, choices=list(choices), default=default))


def checkbox(message: str, choices: Sequence[Any]) -> list[Any]:
    return list(_answer(questionary.checkbox(message, choices=list(choices))))


def confirm(message: str, *, yes: bool, default: bool = False) -> bool:
    """Ask to proceed. ``--yes`` or a non-interactive session both proceed."""
    if yes or not is_interactive():
        return True
    return bool(_answer(questionary.confirm(message, default=default)))


def resolve_editor() -> str | None:
    for var in ("BJ_EDITOR", "VISUAL", "EDITOR"):
        if value := os.environ.get(var):
            return value
    return None


def edit_text(initial: str = "", *, suffix: str = ".md") -> str | None:
    """Open ``$EDITOR`` on ``initial`` and return the result (None if no editor)."""
    editor = resolve_editor()
    if not editor:
        return None
    with tempfile.NamedTemporaryFile("w+", suffix=suffix, delete=False, encoding="utf-8") as handle:
        handle.write(initial)
        path = handle.name
    try:
        subprocess.run([*shlex.split(editor), path], check=True)  # noqa: S603
        return Path(path).read_text(encoding="utf-8")
    finally:
        Path(path).unlink(missing_ok=True)


def run_with_status(label: str, coro: Coroutine[object, object, T]) -> T:
    """Run an async coroutine while showing a spinner (when on a TTY)."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return run(coro)
    with console.status(label):
        return run(coro)


def page(text: str) -> None:
    """Print long text, through the system pager when interactive."""
    pager = os.environ.get("BJ_PAGER", os.environ.get("PAGER"))
    if not sys.stdout.isatty() or pager in ("", "cat"):
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
        return
    with console.pager(styles=True):
        console.print(text, highlight=False)
