"""Tests for git authentication env construction."""

import pytest

from bitbucket_jira_cli import gitauth
from bitbucket_jira_cli.config import BitbucketConfig
from bitbucket_jira_cli.config import Config


def test_username_basic() -> None:
    assert gitauth.bitbucket_git_username(Config()) == "x-bitbucket-api-token-auth"


def test_username_bearer() -> None:
    cfg = Config(bitbucket=BitbucketConfig(auth_mode="bearer"))
    assert gitauth.bitbucket_git_username(cfg) == "x-token-auth"


def test_git_env_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gitauth, "get_token", lambda _backend: None)
    env = gitauth.git_env(Config())
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert "BJ_GIT_PASSWORD" not in env


def test_git_env_with_token(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(gitauth, "get_token", lambda _backend: "tok")
    env = gitauth.git_env(Config())
    assert env["BJ_GIT_PASSWORD"] == "tok"
    assert env["BJ_GIT_USERNAME"] == "x-bitbucket-api-token-auth"
    assert env["GIT_ASKPASS"].endswith("git-askpass.sh")
