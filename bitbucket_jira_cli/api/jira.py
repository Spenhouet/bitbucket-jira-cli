"""Jira Cloud REST API v3 async client.

Uses the current ``/search/jql`` endpoint (the old ``/search`` was removed).
Bodies (comments, descriptions) are ADF documents — see ``api.adf``.
"""

from __future__ import annotations

from typing import Any

from bitbucket_jira_cli.api.base import BaseAsyncClient


class JiraClient(BaseAsyncClient):
    backend = "Jira"

    def __init__(self, site: str, authorization: str) -> None:
        base = site.rstrip("/") + "/rest/api/3"
        super().__init__(base, {"Authorization": authorization})

    # -- identity -----------------------------------------------------------
    async def myself(self) -> dict[str, Any]:
        return await self.get_json("/myself")

    # -- issues -------------------------------------------------------------
    async def get_issue(
        self, key: str, *, fields: list[str] | None = None
    ) -> dict[str, Any]:
        params = {"fields": ",".join(fields)} if fields else None
        return await self.get_json(f"/issue/{key}", params=params)

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
        payload_fields = fields or ["summary", "status", "assignee", "issuetype", "priority"]
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
