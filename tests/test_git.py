"""Tests for branch-key parsing and Bitbucket remote-URL parsing."""

import pytest

from bitbucket_jira_cli.config import BranchKeyConfig
from bitbucket_jira_cli.git import _BB_HTTPS
from bitbucket_jira_cli.git import _BB_SSH
from bitbucket_jira_cli.git import parse_branch_key


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("feature/PROJ-42-thing", "PROJ-42"),
        ("PROJ-42", "PROJ-42"),
        ("bugfix/abc-7_hotfix", "ABC-7"),
        ("main", None),
        ("release/v1.2.3", None),
    ],
)
def test_parse_branch_key_default(branch: str, expected: str | None) -> None:
    assert parse_branch_key(branch, BranchKeyConfig()) == expected


def test_parse_branch_key_prefix_filter() -> None:
    cfg = BranchKeyConfig(project_prefixes=["PROJ"])
    assert parse_branch_key("chore/utf-8-fix", cfg) is None
    assert parse_branch_key("feature/proj-9", cfg) == "PROJ-9"


def test_parse_branch_key_disabled() -> None:
    assert parse_branch_key("feature/PROJ-42", BranchKeyConfig(enabled=False)) is None


@pytest.mark.parametrize(
    ("url", "ws", "repo"),
    [
        ("git@bitbucket.org:myteam/myrepo.git", "myteam", "myrepo"),
        ("https://user@bitbucket.org/myteam/myrepo.git", "myteam", "myrepo"),
        ("https://bitbucket.org/myteam/myrepo", "myteam", "myrepo"),
    ],
)
def test_remote_url_parsing(url: str, ws: str, repo: str) -> None:
    match = _BB_SSH.match(url) or _BB_HTTPS.match(url)
    assert match is not None
    assert match.group("ws") == ws
    assert match.group("repo") == repo
