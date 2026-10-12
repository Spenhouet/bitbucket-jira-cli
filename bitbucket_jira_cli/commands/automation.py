"""`bj automation` - Jira Cloud automation rules.

Rules are managed through the Jira Automation REST API, which is separate from
the Jira platform API. It accepts the Jira credentials from `bj auth login`, but
Atlassian documents only unscoped API tokens for it, and the rule endpoints need
a Jira administrator.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Literal

import typer

from bitbucket_jira_cli.api.automation import project_scope_ari
from bitbucket_jira_cli.api.automation import rule_create_payload
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import automation_client
from bitbucket_jira_cli.context import jira_client
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

automation_app = typer.Typer(
    help="Manage Jira automation rules (needs an unscoped Jira token).", no_args_is_help=True
)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]
UuidArg = Annotated[str, typer.Argument(help="Rule UUID (see `bj automation list`).")]


def _scope_label(aris: list[str] | None) -> str:
    """Short label for a rule's scope ARIs: 'global', 'project/10001', ..."""
    if not aris:
        return "global"
    labels = []
    for ari in aris:
        resource = ari.rsplit(":", 1)[-1]
        labels.append("global" if resource.startswith("site/") else resource)
    return ", ".join(labels)


def _state_label(state: str | None) -> str:
    if state == "ENABLED":
        return "[green]enabled[/green]"
    if state == "DISABLED":
        return "[yellow]disabled[/yellow]"
    return f"[dim]{(state or 'unknown').lower()}[/dim]"


def _render_rules(rules: list[dict[str, Any]]) -> None:
    if not rules:
        console.print("[dim]No automation rules.[/dim]")
        return
    for rule in rules:
        scope = _scope_label(rule.get("ruleScopeARIs"))
        console.print(
            f"[cyan]{rule.get('uuid')}[/cyan] {rule.get('name')} · "
            f"{_state_label(rule.get('state'))} [dim]{scope}[/dim]"
        )


def _render_rule(config: dict[str, Any]) -> None:
    rule = config.get("rule", config)
    trigger = rule.get("trigger") or {}
    console.print(f"[bold]{rule.get('name')}[/bold]")
    console.print(f"uuid:       {rule.get('uuid')}")
    console.print(f"state:      {_state_label(rule.get('state'))}")
    console.print(f"scope:      {_scope_label(rule.get('ruleScopeARIs'))}")
    console.print(f"trigger:    {trigger.get('type')}")
    console.print(f"components: {len(rule.get('components') or [])}")
    if rule.get("description"):
        console.print(f"\n{rule['description']}")


async def _project_scope(config: Any, project: str, cloud_id: str) -> str:
    """Rule-scope ARI for a project key or numeric id."""
    if project.isdigit():
        return project_scope_ari(cloud_id, project)
    async with jira_client(config) as jira:
        project_id = str((await jira.get_project(project))["id"])
    return project_scope_ari(cloud_id, project_id)


@automation_app.command(name="list")
def list_rules(
    state: Annotated[
        Literal["enabled", "disabled"] | None,
        typer.Option("--state", "-s", help="Only rules in this state."),
    ] = None,
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Only rules scoped to this project (key or id)."),
    ] = None,
    trigger: Annotated[
        str | None,
        typer.Option(
            "--trigger",
            help="Only rules with this trigger type, e.g. jira.issue.event.trigger:created.",
        ),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", help="Maximum number of rules.")] = 1000,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List automation rules (name, UUID, state, scope)."""
    config = load_config()

    async def _run() -> list[dict[str, Any]]:
        client, cloud_id = await automation_client(config)
        async with client:
            scope = await _project_scope(config, project, cloud_id) if project else None
            return await client.list_rules(
                state=state.upper() if state else None, trigger=trigger, scope=scope, limit=limit
            )

    rules = run_with_status("Loading automation rules…", _run())
    if not emit(rules, as_json=as_json, jq=jq):
        _render_rules(rules)


@automation_app.command()
def view(uuid: UuidArg, as_json: JsonOpt = False, jq: JqOpt = None) -> None:
    """View one rule; --json prints its full definition."""
    config = load_config()

    async def _run() -> dict[str, Any]:
        client, _ = await automation_client(config)
        async with client:
            return await client.get_rule(uuid)

    rule = run_with_status("Loading rule…", _run())
    if not emit(rule, as_json=as_json, jq=jq):
        _render_rule(rule)


def _set_state(uuid: str, state: str) -> None:
    config = load_config()

    async def _run() -> None:
        client, _ = await automation_client(config)
        async with client:
            await client.set_state(uuid, state)

    run_with_status("Updating rule…", _run())


@automation_app.command()
def enable(uuid: UuidArg) -> None:
    """Enable a rule."""
    _set_state(uuid, "ENABLED")
    success(f"Enabled rule {uuid}")


@automation_app.command()
def disable(uuid: UuidArg) -> None:
    """Disable a rule."""
    _set_state(uuid, "DISABLED")
    success(f"Disabled rule {uuid}")


@automation_app.command()
def export(
    uuid: UuidArg,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write to this file instead of stdout."),
    ] = None,
) -> None:
    """Export a rule definition as JSON, ready for `bj automation import`."""
    config = load_config()

    async def _run() -> dict[str, Any]:
        client, _ = await automation_client(config)
        async with client:
            return await client.get_rule(uuid)

    rule = run_with_status("Loading rule…", _run())
    text = json.dumps(rule, indent=2) + "\n"
    if output is None:
        sys.stdout.write(text)
        return
    output.write_text(text, encoding="utf-8")
    success(f"Exported rule {uuid} to {output}")


def _read_definition(source: str) -> dict[str, Any]:
    try:
        text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"could not read {source}: {exc.strerror or exc}"
        raise BjError(msg) from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        msg = f"{source} is not valid JSON: {exc}"
        raise BjError(msg) from exc
    if not isinstance(data, dict):
        msg = f"{source} does not contain a rule definition object"
        raise BjError(msg)
    return data


@automation_app.command(name="import")
def import_rule(
    source: Annotated[
        str,
        typer.Argument(help="Rule definition file from `bj automation export`, or - for stdin."),
    ],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Name for the new rule.")] = None,
    enabled: Annotated[
        bool, typer.Option("--enable", help="Create the rule enabled (default: disabled).")
    ] = False,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Create a rule from an exported definition.

    The uuid, timestamps and component ids of the source are dropped, so this
    always creates a new rule. It is created disabled unless --enable is set.
    """
    config = load_config()
    try:
        payload = rule_create_payload(_read_definition(source), name=name, enabled=enabled)
    except ValueError as exc:
        raise BjError(str(exc)) from exc

    async def _run() -> dict[str, Any]:
        client, _ = await automation_client(config)
        async with client:
            return await client.create_rule(payload)

    created = run_with_status("Creating rule…", _run())
    if not emit(created, as_json=as_json, jq=jq):
        state = "enabled" if enabled else "disabled"
        success(f"Created rule {payload['rule'].get('name')} ({created.get('ruleUuid')}), {state}")


@automation_app.command()
def delete(uuid: UuidArg, yes: YesOpt = False) -> None:
    """Delete a rule. Jira only deletes disabled rules."""
    config = load_config()
    if not confirm(f"Delete automation rule {uuid}?", yes=yes):
        raise typer.Abort

    async def _run() -> None:
        client, _ = await automation_client(config)
        async with client:
            await client.delete_rule(uuid)

    run_with_status("Deleting…", _run())
    success(f"Deleted rule {uuid}")
