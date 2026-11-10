"""Tests for fetching a Bitbucket Pipelines step log."""

import httpx

from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.api.bitbucket import BASE_URL
from bitbucket_jira_cli.api.bitbucket import BitbucketClient


def test_step_log_accepts_plain_text() -> None:
    """The log endpoint returns plain text and answers 406 to Accept: application/json."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.headers.get("Accept") == "application/json":
            return httpx.Response(406, json={"code": 406, "message": "HTTP 406 Not Acceptable"})
        return httpx.Response(200, text="+ echo hello\nhello\n")

    async def call() -> str:
        client = BitbucketClient("Bearer dummy")
        # Keep the client's default headers so the test sees what Bitbucket would.
        client._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=client._client.headers,
            transport=httpx.MockTransport(handler),
        )
        async with client:
            return await client.pipeline_step_log("ws", "repo", "{p-1}", "{s-1}")

    assert run(call()) == "+ echo hello\nhello\n"
    assert seen[0].url.path.endswith("/pipelines/{p-1}/steps/{s-1}/log")
