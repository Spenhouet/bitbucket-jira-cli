"""`bj config` - read and write non-sensitive settings in config.yml.

Keys use dotted paths, e.g. `git_protocol`, `bitbucket.workspace`,
`branch_key.enabled`. Values are validated against the config schema on write.
"""

from __future__ import annotations

from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.config import save_config
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.ui import console

config_app = typer.Typer(help="Read and write bj configuration.", no_args_is_help=True)


def _flatten(data: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for key, value in data.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            rows.extend(_flatten(value, f"{path}."))
        else:
            rows.append((path, value))
    return rows


def _navigate(data: dict[str, Any], key: str) -> Any:
    node: Any = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            msg = f"No such config key: '{key}'."
            raise BjError(msg)
        node = node[part]
    return node


@config_app.command(name="list")
def list_config() -> None:
    """Print all configuration keys and values."""
    data = load_config().model_dump(mode="json")
    for path, value in _flatten(data):
        console.print(f"[cyan]{path}[/cyan] = {value}")


@config_app.command()
def get(key: Annotated[str, typer.Argument(help="Dotted key, e.g. bitbucket.workspace.")]) -> None:
    """Print a single configuration value."""
    value = _navigate(load_config().model_dump(mode="json"), key)
    console.print(value if value is not None else "")


@config_app.command(name="set")
def set_config(
    key: Annotated[str, typer.Argument(help="Dotted key, e.g. git_protocol.")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Set a configuration value (validated against the schema)."""
    data = load_config().model_dump(mode="json")
    parts = key.split(".")
    node: Any = data
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            msg = f"No such config section: '{part}' in '{key}'."
            raise BjError(msg)
        node = node[part]
    if not isinstance(node, dict) or parts[-1] not in node:
        msg = f"No such config key: '{key}'."
        raise BjError(msg)
    node[parts[-1]] = value
    try:
        validated = Config.model_validate(data)
    except ValueError as exc:
        msg = f"Invalid value for '{key}': {exc}"
        raise BjError(msg) from exc
    save_config(validated)
    console.print(f"Set [cyan]{key}[/cyan] = {value}")
