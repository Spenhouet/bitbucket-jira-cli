"""Tests for Jira base-URL resolution across auth modes."""

import pytest

from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import JiraConfig
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
