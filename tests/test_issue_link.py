"""Tests for `bj issue link` / `links` / `unlink`."""

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bitbucket_jira_cli.commands import issue as issue_cmd
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.main import app
from bitbucket_jira_cli.render import issue_link_parts
from bitbucket_jira_cli.render import remote_link_parts

runner = CliRunner()

LINK_TYPES = [
    {"id": "10000", "name": "Blocks", "inward": "is blocked by", "outward": "blocks"},
    {"id": "10003", "name": "Relates", "inward": "relates to", "outward": "relates to"},
]

ISSUE_LINKS = [
    {
        "id": "20001",
        "type": LINK_TYPES[0],
        "outwardIssue": {"key": "PROJ-2", "fields": {"summary": "Downstream"}},
    },
    {
        "id": "20002",
        "type": LINK_TYPES[0],
        "inwardIssue": {"key": "PROJ-3", "fields": {"summary": "Upstream"}},
    },
]

REMOTE_LINKS = [
    {
        "id": 30001,
        "globalId": "https://example.test/doc",
        "object": {"url": "https://example.test/doc", "title": "Design doc"},
    }
]


class FakeJira:
    """Stand-in for JiraClient recording the calls the link commands make."""

    def __init__(self) -> None:
        self.issue_links: list[tuple[str, str, str]] = []
        self.remote_links: list[tuple[str, str, str, str | None]] = []
        self.deleted: list[tuple[str, str]] = []

    async def __aenter__(self) -> "FakeJira":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def list_issue_link_types(self) -> list[dict[str, Any]]:
        return LINK_TYPES

    async def create_issue_link(self, type_name: str, inward_key: str, outward_key: str) -> None:
        self.issue_links.append((type_name, inward_key, outward_key))

    async def create_remote_link(
        self, key: str, url: str, title: str, *, global_id: str | None = None
    ) -> dict[str, Any]:
        self.remote_links.append((key, url, title, global_id))
        return {"id": 1}

    async def get_issue(self, key: str, **_kwargs: Any) -> dict[str, Any]:
        return {"key": key, "fields": {"issuelinks": ISSUE_LINKS}}

    async def get_remote_links(self, _key: str) -> list[dict[str, Any]]:
        return REMOTE_LINKS

    async def delete_issue_link(self, link_id: str) -> None:
        self.deleted.append(("issue", link_id))

    async def delete_remote_link(self, _key: str, link_id: str) -> None:
        self.deleted.append(("remote", link_id))


@pytest.fixture
def fake_jira(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeJira:
    """Point the issue commands at a fake Jira and an empty config dir."""
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    client = FakeJira()
    monkeypatch.setattr(issue_cmd, "jira_client", lambda _config: client)
    return client


def test_link_commands_registered() -> None:
    """`bj issue --help` lists the three link commands."""
    result = runner.invoke(app, ["issue", "--help"])
    assert result.exit_code == 0
    for name in ("link", "links", "unlink"):
        assert name in result.stdout


def test_link_issue_uses_outward_direction(fake_jira: FakeJira) -> None:
    """`link A B --type blocks` records A as the inward issue, so it reads "A blocks B"."""
    result = runner.invoke(app, ["issue", "link", "PROJ-1", "PROJ-2", "--type", "blocks"])
    assert result.exit_code == 0
    assert fake_jira.issue_links == [("Blocks", "PROJ-1", "PROJ-2")]


def test_link_issue_inward_wording_reverses_the_payload(fake_jira: FakeJira) -> None:
    """`link A B --type "is blocked by"` means B blocks A, so the issues swap."""
    result = runner.invoke(app, ["issue", "link", "PROJ-1", "PROJ-2", "--type", "is blocked by"])
    assert result.exit_code == 0
    assert fake_jira.issue_links == [("Blocks", "PROJ-2", "PROJ-1")]


def test_link_defaults_to_relates_when_non_interactive(fake_jira: FakeJira) -> None:
    """With no --type and no TTY, the link type falls back to Relates."""
    result = runner.invoke(app, ["issue", "link", "PROJ-1", "proj-2"])
    assert result.exit_code == 0
    assert fake_jira.issue_links == [("Relates", "PROJ-1", "PROJ-2")]


def test_link_rejects_unknown_type(fake_jira: FakeJira) -> None:
    """An unknown link type is rejected with the available names."""
    result = runner.invoke(app, ["issue", "link", "PROJ-1", "PROJ-2", "--type", "nope"])
    assert result.exit_code == 1
    assert not fake_jira.issue_links


def test_link_url_attaches_a_remote_link(fake_jira: FakeJira) -> None:
    """A URL target becomes a remote link, with the URL as globalId for idempotency."""
    result = runner.invoke(
        app, ["issue", "link", "PROJ-1", "https://example.test/doc", "--title", "Doc"]
    )
    assert result.exit_code == 0
    assert fake_jira.remote_links == [
        ("PROJ-1", "https://example.test/doc", "Doc", "https://example.test/doc")
    ]


def test_link_rejects_a_target_that_is_neither_key_nor_url(fake_jira: FakeJira) -> None:
    """A bare word is not a valid link target."""
    result = runner.invoke(app, ["issue", "link", "PROJ-1", "whatever"])
    assert result.exit_code == 1
    assert not fake_jira.issue_links
    assert not fake_jira.remote_links


@pytest.mark.usefixtures("fake_jira")
def test_links_lists_both_kinds() -> None:
    """`issue links` shows related issues and attached URLs."""
    result = runner.invoke(app, ["issue", "links", "PROJ-1"])
    assert result.exit_code == 0
    assert "blocks" in result.stdout
    assert "PROJ-2" in result.stdout
    assert "is blocked by" in result.stdout
    assert "PROJ-3" in result.stdout
    assert "example.test/doc" in result.stdout


@pytest.mark.usefixtures("fake_jira")
def test_links_json_output() -> None:
    """--json emits both link collections."""
    result = runner.invoke(app, ["issue", "links", "PROJ-1", "--json"])
    assert result.exit_code == 0
    assert "issueLinks" in result.stdout
    assert "remoteLinks" in result.stdout


def test_unlink_by_issue_key(fake_jira: FakeJira) -> None:
    """The linked issue key identifies the link to delete."""
    result = runner.invoke(app, ["issue", "unlink", "PROJ-1", "PROJ-2", "--yes"])
    assert result.exit_code == 0
    assert fake_jira.deleted == [("issue", "20001")]


def test_unlink_by_url(fake_jira: FakeJira) -> None:
    """A URL identifies the remote link to delete."""
    result = runner.invoke(app, ["issue", "unlink", "PROJ-1", "https://example.test/doc", "--yes"])
    assert result.exit_code == 0
    assert fake_jira.deleted == [("remote", "30001")]


def test_unlink_by_link_id(fake_jira: FakeJira) -> None:
    """A link id from `issue links` also works."""
    result = runner.invoke(app, ["issue", "unlink", "PROJ-1", "20002", "--yes"])
    assert result.exit_code == 0
    assert fake_jira.deleted == [("issue", "20002")]


def test_unlink_unknown_target_errors(fake_jira: FakeJira) -> None:
    """Nothing is deleted when no link matches."""
    result = runner.invoke(app, ["issue", "unlink", "PROJ-1", "PROJ-9", "--yes"])
    assert result.exit_code == 1
    assert not fake_jira.deleted


def test_match_link_type_directions() -> None:
    """Type name and outward wording keep the order; inward wording reverses it."""
    assert issue_cmd._match_link_type("Blocks", LINK_TYPES) == (LINK_TYPES[0], False)
    assert issue_cmd._match_link_type("BLOCKS", LINK_TYPES) == (LINK_TYPES[0], False)
    assert issue_cmd._match_link_type("is blocked by", LINK_TYPES) == (LINK_TYPES[0], True)
    # Relates reads the same in both directions, so it never reverses.
    assert issue_cmd._match_link_type("relates to", LINK_TYPES) == (LINK_TYPES[1], False)
    assert issue_cmd._match_link_type("unknown", LINK_TYPES) is None


def test_split_link_args() -> None:
    """One positional is the target (key comes from the branch); two are key and target."""
    assert issue_cmd._split_link_args("PROJ-1", "PROJ-2") == ("PROJ-1", "PROJ-2")
    assert issue_cmd._split_link_args("PROJ-2", None) == (None, "PROJ-2")
    with pytest.raises(BjError, match="link target"):
        issue_cmd._split_link_args(None, None)


def test_link_parts_pick_the_right_wording() -> None:
    """The side the other issue sits on decides inward vs outward wording."""
    assert issue_link_parts(ISSUE_LINKS[0]) == ("blocks", "PROJ-2", "Downstream")
    assert issue_link_parts(ISSUE_LINKS[1]) == ("is blocked by", "PROJ-3", "Upstream")
    assert remote_link_parts(REMOTE_LINKS[0]) == (
        "links to",
        "https://example.test/doc",
        "Design doc",
    )
