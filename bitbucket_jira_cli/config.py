"""Non-sensitive configuration, stored as YAML — mirrors gh's `config.yml`.

Secrets (API tokens) never live here; they go to the OS keyring or, with
``--insecure-storage``, to a separate ``credentials.yml``. See ``auth.store``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel
from pydantic import Field

APP_NAME = "bitbucket-jira-cli"
# Case-tolerant: branch names are often lowercase (feature/proj-42); the parsed
# key is upper-cased. project_prefixes filters stray matches like "utf-8".
DEFAULT_BRANCH_KEY_PATTERN = r"([A-Za-z][A-Za-z0-9]+-\d+)"


def config_dir() -> Path:
    """Resolve the config directory the way gh does: BJ_CONFIG_DIR, then XDG."""
    if override := os.environ.get("BJ_CONFIG_DIR"):
        return Path(override)
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.yml"


def credentials_path() -> Path:
    return config_dir() / "credentials.yml"


class BitbucketConfig(BaseModel):
    workspace: str | None = None
    email: str | None = None
    auth_mode: Literal["basic", "bearer"] = "basic"


class JiraConfig(BaseModel):
    site: str | None = None  # e.g. https://your-domain.atlassian.net
    email: str | None = None
    # "site": unscoped token on the *.atlassian.net host (Basic auth).
    # "gateway": scoped token on api.atlassian.com/ex/jira/{cloud_id} (least privilege).
    auth_mode: Literal["site", "gateway"] = "site"
    cloud_id: str | None = None


class BranchKeyConfig(BaseModel):
    enabled: bool = True
    pattern: str = DEFAULT_BRANCH_KEY_PATTERN
    project_prefixes: list[str] = Field(default_factory=list)


class TransitionsConfig(BaseModel):
    on_pr_create: str | None = "In Progress"
    on_pr_merge: str | None = "Done"


class Config(BaseModel):
    version: int = 1
    git_protocol: Literal["https", "ssh"] = "https"
    editor: str | None = None
    pager: str | None = None
    browser: str | None = None
    bitbucket: BitbucketConfig = Field(default_factory=BitbucketConfig)
    jira: JiraConfig = Field(default_factory=JiraConfig)
    branch_key: BranchKeyConfig = Field(default_factory=BranchKeyConfig)
    transitions: TransitionsConfig = Field(default_factory=TransitionsConfig)


def load_config() -> Config:
    path = config_path()
    if not path.exists():
        return Config()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Config.model_validate(data)


def save_config(config: Config) -> None:
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    path = config_path()
    path.write_text(
        yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    path.chmod(0o600)
