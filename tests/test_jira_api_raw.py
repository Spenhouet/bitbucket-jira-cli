"""Tests for how `bj api --backend jira` resolves request paths."""

from typing import Any

import httpx
import pytest

from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.api.jira import JiraClient
from bitbucket_jira_cli.errors import ApiError

GATEWAY = "https://api.atlassian.com/ex/jira/c-1/rest/api/3"
SITE = "https://ex.atlassian.net/rest/api/3"


def _client(base_url: str, seen: list[str]) -> JiraClient:
    """A JiraClient whose transport records URLs and mimics the gateway.

    The real gateway answers a path it doesn't know (such as a doubled
    ``/rest/api/3/rest/api/3``) with 401 "scope does not match".
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        seen.append(url)
        if "/rest/api/3/rest/" in url:
            return httpx.Response(401, json={"code": 401, "message": "scope does not match"})
        return httpx.Response(200, json={"ok": True})

    client = JiraClient(base_url, "Basic dummy")
    client._client = httpx.AsyncClient(base_url=base_url, transport=httpx.MockTransport(handler))
    return client


async def _raw(base_url: str, path: str, seen: list[str]) -> Any:
    async with _client(base_url, seen) as client:
        return await client.raw("GET", path)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/myself", f"{GATEWAY}/myself"),
        ("myself", f"{GATEWAY}/myself"),
        ("/rest/api/3/myself", f"{GATEWAY}/myself"),
        ("rest/api/3/project/PROJ", f"{GATEWAY}/project/PROJ"),
        (
            "/rest/api/3/issue/createmeta/PROJ/issuetypes",
            f"{GATEWAY}/issue/createmeta/PROJ/issuetypes",
        ),
        ("/rest/api/2/myself", "https://api.atlassian.com/ex/jira/c-1/rest/api/2/myself"),
        ("rest/agile/1.0/board", "https://api.atlassian.com/ex/jira/c-1/rest/agile/1.0/board"),
    ],
)
def test_gateway_paths_are_not_doubled(path: str, expected: str) -> None:
    """Short and full REST paths both land on the right gateway URL."""
    seen: list[str] = []
    assert run(_raw(GATEWAY, path, seen)) == {"ok": True}
    assert seen == [expected]


def test_site_mode_full_path() -> None:
    """A full REST path also resolves against the site host in site mode."""
    seen: list[str] = []
    run(_raw(SITE, "/rest/api/3/myself", seen))
    assert seen == [f"{SITE}/myself"]


def test_doubled_path_is_what_the_gateway_rejects() -> None:
    """Guard for the mock: a doubled prefix is the 401 users saw."""
    seen: list[str] = []
    with pytest.raises(ApiError, match="scope does not match"):
        run(_raw(GATEWAY, "/rest/api/3/rest/api/3/myself", seen))
