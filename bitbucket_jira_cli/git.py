"""Local git helpers: current branch, Bitbucket remote parsing, branch keys."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bitbucket_jira_cli.errors import NotInRepoError

if TYPE_CHECKING:
    from bitbucket_jira_cli.config import BranchKeyConfig


@dataclass(frozen=True)
class RepoRef:
    workspace: str
    repo_slug: str

    def __str__(self) -> str:
        return f"{self.workspace}/{self.repo_slug}"


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_branch() -> str | None:
    return _git("rev-parse", "--abbrev-ref", "HEAD") or None


def last_commit_subject() -> str | None:
    return _git("log", "-1", "--pretty=%s") or None


def last_commit_body() -> str | None:
    return _git("log", "-1", "--pretty=%b") or None


def _git_env(*args: str, env: dict[str, str] | None) -> str | None:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except FileNotFoundError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def checkout_branch(
    branch: str, remote: str = "origin", *, env: dict[str, str] | None = None
) -> None:
    """Fetch and check out ``branch`` from ``remote`` (create a local branch).

    ``env`` (from ``gitauth.git_env``) authenticates the fetch for HTTPS remotes.
    """
    _git_env("fetch", remote, branch, env=env)
    if _git_env("checkout", branch, env=env) is not None:
        return
    if _git_env("checkout", "-b", branch, "--track", f"{remote}/{branch}", env=env) is not None:
        return
    msg = f"Could not check out branch '{branch}'."
    raise NotInRepoError(msg)


def _remote_url(remote: str = "origin") -> str | None:
    return _git("remote", "get-url", remote)


# git@bitbucket.org:workspace/repo.git  |  https://bitbucket.org/workspace/repo.git
_BB_SSH = re.compile(r"^git@bitbucket\.org:(?P<ws>[^/]+)/(?P<repo>.+?)(?:\.git)?$")
_BB_HTTPS = re.compile(
    r"^https?://(?:[^@/]+@)?bitbucket\.org/(?P<ws>[^/]+)/(?P<repo>.+?)(?:\.git)?/?$"
)


def repo_ref_from_remote(remote: str = "origin") -> RepoRef | None:
    url = _remote_url(remote)
    if not url:
        return None
    for pattern in (_BB_SSH, _BB_HTTPS):
        if match := pattern.match(url):
            return RepoRef(match.group("ws"), match.group("repo"))
    return None


def require_repo_ref() -> RepoRef:
    ref = repo_ref_from_remote()
    if ref is None:
        msg = (
            "Not in a Bitbucket Cloud repository (no 'origin' remote pointing at "
            "bitbucket.org). Pass --repo WORKSPACE/REPO or run inside a clone."
        )
        raise NotInRepoError(msg)
    return ref


def parse_branch_key(branch: str, config: BranchKeyConfig) -> str | None:
    """Extract the first Jira key from a branch name per the configured rule."""
    if not config.enabled or not branch:
        return None
    for match in re.finditer(config.pattern, branch):
        key = match.group(1) if match.groups() else match.group(0)
        prefix = key.split("-", 1)[0]
        if config.project_prefixes and prefix.upper() not in {
            p.upper() for p in config.project_prefixes
        }:
            continue
        return key.upper()
    return None
