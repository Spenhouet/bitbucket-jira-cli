"""Jira Cloud REST API v3 async client.

Uses the current ``/search/jql`` endpoint (the old ``/search`` was removed).
Bodies (comments, descriptions) are ADF documents — see ``api.adf``.
"""

from __future__ import annotations

from typing import Any

import httpx

from bitbucket_jira_cli.api.base import DEFAULT_TIMEOUT
from bitbucket_jira_cli.api.base import BaseAsyncClient
from bitbucket_jira_cli.errors import ApiError


async def fetch_cloud_id(site: str) -> str:
    """Resolve a site's cloudId from its public tenant_info endpoint.

    Needed to address a site through the api.atlassian.com/ex/jira/{cloudId}
    gateway (scoped-token mode). No authentication required.
    """
    backend = "Jira"
    url = site.rstrip("/") + "/_edge/tenant_info"
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        response = await client.get(url)
    if response.status_code >= httpx.codes.BAD_REQUEST:
        msg = f"could not resolve cloudId from {url}"
        raise ApiError(backend, response.status_code, msg)
    cloud_id = response.json().get("cloudId")
    if not cloud_id:
        msg = "tenant_info returned no cloudId"
        raise ApiError(backend, response.status_code, msg)
    return str(cloud_id)


class JiraClient(BaseAsyncClient):
    backend = "Jira"

    def __init__(self, base_url: str, authorization: str) -> None:
        super().__init__(base_url, {"Authorization": authorization})

    # -- identity -----------------------------------------------------------
    async def myself(self) -> dict[str, Any]:
        return await self.get_json("/myself")

    # -- issues -------------------------------------------------------------
    async def get_issue(
        self, key: str, *, fields: list[str] | None = None, expand: list[str] | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if fields:
            params["fields"] = ",".join(fields)
        if expand:
            params["expand"] = ",".join(expand)
        return await self.get_json(f"/issue/{key}", params=params or None)

    async def get_editmeta(self, key: str) -> dict[str, Any]:
        data = await self.get_json(f"/issue/{key}/editmeta")
        return data.get("fields", {})

    async def search_assignable_users(
        self, query: str, *, issue_key: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        return await self.get_json(
            "/user/assignable/search",
            params={"query": query, "issueKey": issue_key, "maxResults": limit},
        )

    async def create_issue(self, body: dict[str, Any]) -> dict[str, Any]:
        response = await self.request("POST", "/issue", json=body)
        return response.json()

    async def edit_issue(self, key: str, body: dict[str, Any]) -> None:
        await self.request("PUT", f"/issue/{key}", json=body)

    async def search(
        self, jql: str, *, fields: list[str] | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        token: str | None = None
        payload_fields = fields or [
            "summary",
            "status",
            "assignee",
            "issuetype",
            "priority",
            "updated",
        ]
        while True:
            body: dict[str, Any] = {
                "jql": jql,
                "maxResults": min(limit - len(issues), 100),
                "fields": payload_fields,
            }
            if token:
                body["nextPageToken"] = token
            response = await self.request("POST", "/search/jql", json=body)
            data = response.json()
            issues.extend(data.get("issues", []))
            token = data.get("nextPageToken")
            if not token or len(issues) >= limit:
                break
        return issues[:limit]

    # -- comments -----------------------------------------------------------
    async def add_comment(self, key: str, adf_body: dict[str, Any]) -> dict[str, Any]:
        response = await self.request("POST", f"/issue/{key}/comment", json={"body": adf_body})
        return response.json()

    async def list_comments(self, key: str) -> list[dict[str, Any]]:
        data = await self.get_json(f"/issue/{key}/comment")
        return data.get("comments", [])

    # -- transitions --------------------------------------------------------
    async def get_transitions(self, key: str) -> list[dict[str, Any]]:
        data = await self.get_json(f"/issue/{key}/transitions")
        return data.get("transitions", [])

    async def transition_issue(self, key: str, transition_id: str) -> None:
        await self.request(
            "POST", f"/issue/{key}/transitions", json={"transition": {"id": transition_id}}
        )

    # -- remote links (link a PR URL to an issue) ---------------------------
    async def create_remote_link(
        self, key: str, url: str, title: str, *, global_id: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"object": {"url": url, "title": title}}
        if global_id:
            body["globalId"] = global_id
        response = await self.request("POST", f"/issue/{key}/remotelink", json=body)
        return response.json()

    async def get_remote_links(self, key: str) -> list[dict[str, Any]]:
        return await self.get_json(f"/issue/{key}/remotelink")

    # -- generic passthrough (bj api) --------------------------------------
    async def raw(
        self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None
    ) -> Any:
        response = await self.request(method, path, params=params, json=json)
        try:
            return response.json()
        except ValueError:
            return response.text
