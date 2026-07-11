"""Shared command helpers: repo resolution and machine-readable output."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Any

from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.git import RepoRef
from bitbucket_jira_cli.git import require_repo_ref
from bitbucket_jira_cli.ui import print_json


def resolve_repo(repo: str | None) -> RepoRef:
    """Resolve WORKSPACE/REPO from an explicit ``--repo`` or the git remote."""
    if repo:
        if repo.count("/") != 1:
            msg = "--repo must be in WORKSPACE/REPO format."
            raise BjError(msg)
        workspace, slug = repo.split("/", 1)
        return RepoRef(workspace, slug)
    return require_repo_ref()


def resolve_workspace(workspace: str | None, config_workspace: str | None) -> str:
    ws = workspace or config_workspace
    if not ws:
        msg = (
            "No workspace given. Pass it as an argument (e.g. `bj repo list myteam`), "
            "set a default with `bj repo set-default myteam/repo`, or run inside a "
            "Bitbucket clone so it can be read from the remote."
        )
        raise BjError(msg)
    return ws


def _run_jq(data: Any, expr: str) -> None:
    jq_bin = shutil.which("jq")
    if not jq_bin:
        msg = "`--jq` requires the `jq` binary on PATH."
        raise BjError(msg)
    proc = subprocess.run(  # noqa: S603
        [jq_bin, expr],
        input=json.dumps(data, default=str),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise BjError(proc.stderr.strip())
    sys.stdout.write(proc.stdout)


def emit(data: Any, *, as_json: bool, jq: str | None) -> bool:
    """Emit machine output if requested. Returns True if it did (skip render)."""
    if jq is not None:
        _run_jq(data, jq)
        return True
    if as_json:
        print_json(data)
        return True
    return False
