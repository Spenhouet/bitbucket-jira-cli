"""Authenticate git subprocesses to Bitbucket using the stored API token.

Git-over-HTTPS on bitbucket.org does not accept the Atlassian email as the
username (only the REST API does); the correct git username for an API token is
``x-bitbucket-api-token-auth`` (or ``x-token-auth`` for access tokens). We wire
that up via a GIT_ASKPASS helper so ``git clone``/``fetch`` authenticate
non-interactively (agent-friendly) without ever putting the token in the URL,
argv, or a committed config. SSH remotes ignore all of this and use the user's
keys.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from bitbucket_jira_cli.auth.store import get_token
from bitbucket_jira_cli.config import config_dir

if TYPE_CHECKING:
    from pathlib import Path

    from bitbucket_jira_cli.config import Config

_ASKPASS_SCRIPT = """#!/bin/sh
# git calls this for each credential prompt; answer by prompt type.
case "$1" in
  *[Uu]sername*) printf '%s' "$BJ_GIT_USERNAME" ;;
  *) printf '%s' "$BJ_GIT_PASSWORD" ;;
esac
"""


def _askpass_path() -> Path:
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "git-askpass.sh"
    if not path.exists() or path.read_text(encoding="utf-8") != _ASKPASS_SCRIPT:
        path.write_text(_ASKPASS_SCRIPT, encoding="utf-8")
    path.chmod(0o700)
    return path


def bitbucket_git_username(config: Config) -> str:
    if config.bitbucket.auth_mode == "bearer":
        return "x-token-auth"
    return "x-bitbucket-api-token-auth"


def git_env(config: Config) -> dict[str, str]:
    """Return a git subprocess env that authenticates HTTPS Bitbucket via the token.

    Falls back to the plain environment (with prompts disabled) when no token is
    stored — SSH remotes work regardless; HTTPS then fails fast instead of hanging.
    """
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    token = get_token("bitbucket")
    if token:
        env["GIT_ASKPASS"] = str(_askpass_path())
        env["BJ_GIT_USERNAME"] = bitbucket_git_username(config)
        env["BJ_GIT_PASSWORD"] = token
    return env
