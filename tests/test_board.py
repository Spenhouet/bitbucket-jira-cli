"""Tests for listing Jira boards and sprints through the agile API."""

from typing import Any

import httpx

from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.api.jira import JiraClient

SITE = "https://ex.atlassian.net/rest/api/3"


def _client(total: int, seen: list[httpx.Request], page_size: int = 50) -> JiraClient:
    """A JiraClient whose agile endpoints serve ``total`` items in pages of ``page_size``."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        start = int(request.url.params.get("startAt", 0))
        end = min(start + page_size, total)
        values = [{"id": i, "name": f"Item {i}"} for i in range(start, end)]
        return httpx.Response(
            200,
            json={
                "startAt": start,
                "maxResults": page_size,
                "isLast": end >= total,
                "values": values,
            },
        )

    client = JiraClient(SITE, "Basic dummy")
    client._client = httpx.AsyncClient(base_url=SITE, transport=httpx.MockTransport(handler))
    return client


async def _sprints(total: int, seen: list[httpx.Request]) -> list[dict[str, Any]]:
    async with _client(total, seen) as client:
        return await client.list_sprints(7)


async def _boards(
    total: int, seen: list[httpx.Request], project: str | None = None
) -> list[dict[str, Any]]:
    async with _client(total, seen) as client:
        return await client.list_boards(project=project)


def test_list_sprints_follows_every_page() -> None:
    seen: list[httpx.Request] = []
    sprints = run(_sprints(75, seen))
    assert [s["id"] for s in sprints] == list(range(75))
    assert [r.url.params["startAt"] for r in seen] == ["0", "50"]


def test_list_sprints_single_page_makes_one_request() -> None:
    seen: list[httpx.Request] = []
    run(_sprints(3, seen))
    assert len(seen) == 1


def test_list_boards_follows_every_page() -> None:
    seen: list[httpx.Request] = []
    boards = run(_boards(120, seen))
    assert len(boards) == 120
    assert [r.url.params["startAt"] for r in seen] == ["0", "50", "100"]


def test_list_boards_keeps_project_filter_on_every_page() -> None:
    seen: list[httpx.Request] = []
    run(_boards(60, seen, project="PROJ"))
    assert [r.url.params["projectKeyOrId"] for r in seen] == ["PROJ", "PROJ"]


def test_empty_page_without_is_last_stops() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"values": [], "isLast": False})

    async def _go() -> list[dict[str, Any]]:
        client = JiraClient(SITE, "Basic dummy")
        client._client = httpx.AsyncClient(base_url=SITE, transport=httpx.MockTransport(handler))
        async with client:
            return await client.list_sprints(7)

    assert run(_go()) == []
