"""Tests for `bj pr comment`, focused on pending (draft) review comments."""

from pathlib import Path
from typing import Any

import pytest
from rich.text import Text
from typer.testing import CliRunner

from bitbucket_jira_cli.commands import pr as pr_cmd
from bitbucket_jira_cli.main import app
from bitbucket_jira_cli.render import _render_comment_threads
from bitbucket_jira_cli.ui import console

runner = CliRunner()


class FakeBitbucket:
    """Stand-in for BitbucketClient recording the comments it is asked to add."""

    def __init__(self) -> None:
        self.added: list[dict[str, Any]] = []
        self.keep_pending = True

    async def __aenter__(self) -> "FakeBitbucket":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def add_pr_comment(
        self,
        _workspace: str,
        _repo_slug: str,
        pr_id: int,
        text: str,
        *,
        inline: dict[str, Any] | None = None,
        parent_id: int | None = None,
        pending: bool = False,
    ) -> dict[str, Any]:
        call = {"pr_id": pr_id, "text": text, "inline": inline, "parent_id": parent_id}
        self.added.append({**call, "pending": pending})
        return {"id": 7, "pending": pending and self.keep_pending}


@pytest.fixture
def fake_bb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeBitbucket:
    """Point the pr commands at a fake Bitbucket and an empty config dir."""
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    client = FakeBitbucket()
    monkeypatch.setattr(pr_cmd, "_bb", lambda _config: client)
    return client


def _comment(*args: str) -> Any:
    return runner.invoke(app, ["pr", "comment", "42", "--repo", "ws/repo", *args])


def test_comment_is_published_by_default(fake_bb: FakeBitbucket) -> None:
    """Without --pending the comment is posted as a normal, visible comment."""
    result = _comment("--body", "hi")
    assert result.exit_code == 0
    assert fake_bb.added == [
        {"pr_id": 42, "text": "hi", "inline": None, "parent_id": None, "pending": False}
    ]


def test_pending_inline_comment(fake_bb: FakeBitbucket) -> None:
    """--pending is passed through for an inline comment and reported as pending."""
    result = _comment("--body", "nit", "--file", "src/app.py", "--line", "3", "--pending")
    assert result.exit_code == 0
    assert fake_bb.added[0]["pending"] is True
    assert fake_bb.added[0]["inline"] == {"path": "src/app.py", "to": 3}
    assert "pending inline comment 7" in Text.from_ansi(result.output).plain


def test_pending_reply(fake_bb: FakeBitbucket) -> None:
    """--pending also works for a reply to an existing comment."""
    result = _comment("--body", "agreed", "--reply-to", "5", "--pending")
    assert result.exit_code == 0
    assert fake_bb.added[0]["parent_id"] == 5
    assert fake_bb.added[0]["pending"] is True


def test_pending_warns_when_bitbucket_publishes_anyway(fake_bb: FakeBitbucket) -> None:
    """If the response is not pending, the user is told the comment is already public."""
    fake_bb.keep_pending = False
    result = _comment("--body", "hi", "--pending")
    assert result.exit_code == 0
    assert "did not keep the comment pending" in Text.from_ansi(result.output).plain


@pytest.mark.parametrize("flag", ["--edit", "--delete", "--resolve", "--unresolve"])
def test_pending_rejected_with_management_flags(fake_bb: FakeBitbucket, flag: str) -> None:
    """--pending makes no sense when editing or managing an existing comment."""
    result = _comment(flag, "5", "--body", "x", "--pending")
    assert result.exit_code == 1
    assert not fake_bb.added


def test_threads_mark_pending_comments() -> None:
    """Pending comments are tagged in the rendered thread view."""
    comments = [
        {"id": 1, "user": {"display_name": "Ann"}, "content": {"raw": "draft"}, "pending": True},
        {"id": 2, "user": {"display_name": "Bob"}, "content": {"raw": "live"}, "pending": False},
    ]
    with console.capture() as capture:
        _render_comment_threads(comments)
    lines = Text.from_ansi(capture.get()).plain.splitlines()
    assert "(pending)" in lines[0]
    assert "(pending)" not in lines[1]
