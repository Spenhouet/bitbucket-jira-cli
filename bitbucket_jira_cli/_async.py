"""Bridge between Typer's sync commands and the async httpx clients."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from typing import TypeVar

if TYPE_CHECKING:
    from collections.abc import Coroutine

T = TypeVar("T")


def run(coro: Coroutine[object, object, T]) -> T:
    """Run an async command body to completion from a sync Typer callback."""
    return asyncio.run(coro)
