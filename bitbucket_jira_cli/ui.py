"""Shared output helpers: a rich console and JSON/scripting output."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def ensure_safe_output() -> None:
    """Print '?' for characters the output encoding cannot represent, instead of crashing.

    On Windows, stdout often uses a legacy code page such as cp1252 (for example when
    output is piped). Symbols like the check mark then raise UnicodeEncodeError, and a
    command that already succeeded exits with a traceback.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None and getattr(stream, "errors", None) == "strict":
            reconfigure(errors="replace")


def print_json(data: Any) -> None:
    """Emit machine-readable JSON to stdout (for `--json`)."""
    sys.stdout.write(json.dumps(data, indent=2, default=str) + "\n")


def print_error(message: str) -> None:
    err_console.print(f"[red]error:[/red] {message}")


def success(message: str) -> None:
    # Informational — goes to stderr so `--json` / rendered stdout stays clean.
    err_console.print(f"[green]✓[/green] {message}")
