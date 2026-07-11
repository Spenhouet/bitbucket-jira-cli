"""Shared output helpers: a rich console and JSON/scripting output."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def print_json(data: Any) -> None:
    """Emit machine-readable JSON to stdout (for `--json`)."""
    sys.stdout.write(json.dumps(data, indent=2, default=str) + "\n")


def print_error(message: str) -> None:
    err_console.print(f"[red]error:[/red] {message}")


def success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")
