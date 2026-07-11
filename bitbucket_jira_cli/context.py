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


def jira_client(config: Config) -> JiraClient:
    token = get_token("jira")
    if not token:
        msg = "Not logged in to Jira. Run `bj auth login`."
        raise AuthError(msg)
    site = config.jira.site
    email = config.jira.email
    if not site or not email:
        msg = "Jira site/email are not configured. Run `bj auth login`."
        raise AuthError(msg)
    return JiraClient(site, basic_header(email, token))
