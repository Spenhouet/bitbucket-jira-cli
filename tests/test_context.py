"""Tests for Jira base-URL resolution across auth modes."""

import pytest

from bitbucket_jira_cli.commands.pr import _compose_title_body
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import JiraConfig
from bitbucket_jira_cli.context import jira_browse_url
from bitbucket_jira_cli.context import jira_rest_base
from bitbucket_jira_cli.errors import AuthError


def test_site_mode_base() -> None:
    cfg = Config(jira=JiraConfig(site="https://ex.atlassian.net/", auth_mode="site"))
    assert jira_rest_base(cfg) == "https://ex.atlassian.net/rest/api/3"


def test_gateway_mode_base() -> None:
    cfg = Config(
        jira=JiraConfig(site="https://ex.atlassian.net", auth_mode="gateway", cloud_id="c-1")
    )
    assert jira_rest_base(cfg) == "https://api.atlassian.com/ex/jira/c-1/rest/api/3"


def test_gateway_without_cloud_id_errors() -> None:
    cfg = Config(jira=JiraConfig(site="https://ex.atlassian.net", auth_mode="gateway"))
    with pytest.raises(AuthError, match="cloud_id"):
        jira_rest_base(cfg)


def test_site_mode_without_site_errors() -> None:
    cfg = Config(jira=JiraConfig(auth_mode="site"))
    with pytest.raises(AuthError, match="site is not configured"):
        jira_rest_base(cfg)


def test_browse_url_uses_the_site_host_in_gateway_mode() -> None:
    cfg = Config(
        jira=JiraConfig(site="https://ex.atlassian.net/", auth_mode="gateway", cloud_id="c-1")
    )
    assert jira_browse_url(cfg, "PROJ-42") == "https://ex.atlassian.net/browse/PROJ-42"


def test_browse_url_is_none_without_a_site() -> None:
    assert jira_browse_url(Config(jira=JiraConfig()), "PROJ-42") is None


def _ctx(ticket_url: str | None) -> dict[str, object]:
    return {"ticket_summary": "", "ticket_url": ticket_url, "members": []}


def test_pr_body_links_the_ticket() -> None:
    _, body = _compose_title_body(
        _ctx("https://ex.atlassian.net/browse/PROJ-42"),
        "PROJ-42",
        title="A title",
        body="Some change.",
        fill=False,
        editor=False,
    )
    assert body == "Some change.\n\nJira: [PROJ-42](https://ex.atlassian.net/browse/PROJ-42)"


def test_pr_body_falls_back_to_the_bare_key_without_a_site() -> None:
    _, body = _compose_title_body(
        _ctx(None), "PROJ-42", title="A title", body="Some change.", fill=False, editor=False
    )
    assert body == "Some change.\n\nJira: PROJ-42"


def test_pr_body_keeps_a_ticket_the_author_already_mentioned() -> None:
    _, body = _compose_title_body(
        _ctx("https://ex.atlassian.net/browse/PROJ-42"),
        "PROJ-42",
        title="A title",
        body="Fixes PROJ-42.",
        fill=False,
        editor=False,
    )
    assert body == "Fixes PROJ-42."
