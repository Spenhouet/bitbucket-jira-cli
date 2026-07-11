"""Build authorized API clients from stored config + credentials."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bitbucket_jira_cli.api.bitbucket import BitbucketClient
from bitbucket_jira_cli.api.jira import JiraClient
from bitbucket_jira_cli.auth.store import basic_header
from bitbucket_jira_cli.auth.store import get_token
from bitbucket_jira_cli.errors import AuthError

if TYPE_CHECKING:
    from bitbucket_jira_cli.config import Config


def bitbucket_authorization(config: Config) -> str:
    token = get_token("bitbucket")
    if not token:
        msg = "Not logged in to Bitbucket. Run `bj auth login`."
        raise AuthError(msg)
    if config.bitbucket.auth_mode == "bearer":
        return f"Bearer {token}"
    email = config.bitbucket.email
    if not email:
        msg = "Bitbucket email is not configured. Run `bj auth login`."
        raise AuthError(msg)
    return basic_header(email, token)


def bitbucket_client(config: Config) -> BitbucketClient:
    return BitbucketClient(bitbucket_authorization(config))


def jira_rest_base(config: Config) -> str:
    """REST v3 base URL for the configured mode: site host or the gateway."""
    if config.jira.auth_mode == "gateway":
        if not config.jira.cloud_id:
            msg = "Jira gateway mode has no cloud_id. Run `bj auth login --jira`."
            raise AuthError(msg)
        return f"https://api.atlassian.com/ex/jira/{config.jira.cloud_id}/rest/api/3"
    if not config.jira.site:
        msg = "Jira site is not configured. Run `bj auth login`."
        raise AuthError(msg)
    return config.jira.site.rstrip("/") + "/rest/api/3"


def jira_client(config: Config) -> JiraClient:
    token = get_token("jira")
    if not token:
        msg = "Not logged in to Jira. Run `bj auth login`."
        raise AuthError(msg)
    email = config.jira.email
    if not email:
        msg = "Jira email is not configured. Run `bj auth login`."
        raise AuthError(msg)
    return JiraClient(jira_rest_base(config), basic_header(email, token))


def jira_client_or_none(config: Config) -> JiraClient | None:
    """Like ``jira_client`` but returns None when Jira isn't fully configured."""
    if not (config.jira.email and get_token("jira")):
        return None
    if config.jira.auth_mode == "gateway" and not config.jira.cloud_id:
        return None
    if config.jira.auth_mode == "site" and not config.jira.site:
        return None
    return JiraClient(
        jira_rest_base(config), basic_header(config.jira.email, get_token("jira") or "")
    )
