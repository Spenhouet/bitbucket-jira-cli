"""`bj pipeline` — Bitbucket Pipelines (the gh run analog)."""

from __future__ import annotations

from typing import Annotated
from typing import Any

import typer

from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.commands._common import emit
from bitbucket_jira_cli.commands._common import resolve_repo
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import load_config
from bitbucket_jira_cli.context import bitbucket_authorization
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.git import RepoRef
from bitbucket_jira_cli.git import current_branch
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import page
from bitbucket_jira_cli.interaction import run_with_status
from bitbucket_jira_cli.render import render_pipeline
from bitbucket_jira_cli.render import render_pipeline_list
from bitbucket_jira_cli.ui import success

pipeline_app = typer.Typer(help="Work with Bitbucket Pipelines.", no_args_is_help=True)

JsonOpt = Annotated[bool, typer.Option("--json", help="Output raw JSON.")]
JqOpt = Annotated[str | None, typer.Option("--jq", "-q", help="Filter JSON with a jq expression.")]
RepoOpt = Annotated[str | None, typer.Option("--repo", "-R", help="Target repo as WORKSPACE/REPO.")]
YesOpt = Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")]


def _bb(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


def _wrap_uuid(value: str) -> str:
    return value if value.startswith("{") else f"{{{value}}}"


async def _resolve_uuid(client: BitbucketClient, ref: RepoRef, ident: str) -> str:
    if ident.isdigit():
        pipelines = await client.list_pipelines(ref.workspace, ref.repo_slug, limit=100)
        for pipeline in pipelines:
            if str(pipeline.get("build_number")) == ident:
                return str(pipeline["uuid"])
        msg = f"No pipeline with build number {ident}."
        raise BjError(msg)
    return _wrap_uuid(ident)


@pipeline_app.command(name="list")
def list_pipelines(
    limit: Annotated[int, typer.Option("--limit", "-L", help="Max results.")] = 30,
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """List recent pipeline runs."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> list[dict[str, Any]]:
        async with _bb(config) as client:
            return await client.list_pipelines(ref.workspace, ref.repo_slug, limit=limit)

    pipelines = run_with_status("Loading pipelines…", _run())
    if not emit(pipelines, as_json=as_json, jq=jq):
        render_pipeline_list(pipelines)


@pipeline_app.command()
def view(
    pipeline: Annotated[str, typer.Argument(help="Build number or pipeline UUID.")],
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """View a pipeline run and its steps."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> tuple[dict[str, Any], list[dict[str, Any]]]:
        async with _bb(config) as client:
            uuid = await _resolve_uuid(client, ref, pipeline)
            obj = await client.get_pipeline(ref.workspace, ref.repo_slug, uuid)
            steps = await client.list_pipeline_steps(ref.workspace, ref.repo_slug, uuid)
            return obj, steps

    obj, steps = run_with_status("Loading pipeline…", _run())
    if not emit({"pipeline": obj, "steps": steps}, as_json=as_json, jq=jq):
        render_pipeline(obj, steps)


@pipeline_app.command()
def logs(
    pipeline: Annotated[str, typer.Argument(help="Build number or pipeline UUID.")],
    step: Annotated[
        int | None, typer.Option("--step", help="1-based step index (default: all).")
    ] = None,
    repo: RepoOpt = None,
) -> None:
    """Print the logs for a pipeline's steps."""
    config = load_config()
    ref = resolve_repo(repo)

    async def _run() -> list[tuple[str, str]]:
        async with _bb(config) as client:
            uuid = await _resolve_uuid(client, ref, pipeline)
            steps = await client.list_pipeline_steps(ref.workspace, ref.repo_slug, uuid)
            chosen = steps if step is None else steps[step - 1 : step]
            out: list[tuple[str, str]] = []
            for s in chosen:
                log_text = await client.pipeline_step_log(
                    ref.workspace, ref.repo_slug, uuid, str(s.get("uuid"))
                )
                out.append((s.get("name", "(step)"), log_text))
            return out

    sections = run_with_status("Loading logs…", _run())
    rendered = "\n".join(f"===== {name} =====\n{text}" for name, text in sections)
    page(rendered)


@pipeline_app.command(name="run")
def run_pipeline(
    branch: Annotated[
        str | None, typer.Option("--branch", help="Ref to run on (default: current).")
    ] = None,
    custom: Annotated[
        str | None, typer.Option("--pipeline", help="Custom pipeline name to run.")
    ] = None,
    repo: RepoOpt = None,
    as_json: JsonOpt = False,
    jq: JqOpt = None,
) -> None:
    """Trigger a pipeline run."""
    config = load_config()
    ref = resolve_repo(repo)
    ref_name = branch or current_branch()
    if not ref_name:
        msg = "No branch given and no current git branch."
        raise BjError(msg)
    target: dict[str, Any] = {
        "ref_type": "branch",
        "type": "pipeline_ref_target",
        "ref_name": ref_name,
    }
    if custom:
        target["selector"] = {"type": "custom", "pattern": custom}

    async def _run() -> dict[str, Any]:
        async with _bb(config) as client:
            return await client.run_pipeline(ref.workspace, ref.repo_slug, {"target": target})

    result = run_with_status("Triggering pipeline…", _run())
    if not emit(result, as_json=as_json, jq=jq):
        success(f"Triggered pipeline #{result.get('build_number')} on {ref_name}")


@pipeline_app.command()
def stop(
    pipeline: Annotated[str, typer.Argument(help="Build number or pipeline UUID.")],
    yes: YesOpt = False,
    repo: RepoOpt = None,
) -> None:
    """Stop a running pipeline."""
    config = load_config()
    ref = resolve_repo(repo)
    if not confirm(f"Stop pipeline {pipeline}?", yes=yes):
        raise typer.Abort

    async def _run() -> None:
        async with _bb(config) as client:
            uuid = await _resolve_uuid(client, ref, pipeline)
            await client.stop_pipeline(ref.workspace, ref.repo_slug, uuid)

    run_with_status("Stopping…", _run())
    success(f"Stopped pipeline {pipeline}")
