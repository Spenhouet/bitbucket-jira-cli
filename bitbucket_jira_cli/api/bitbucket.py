"""Bitbucket Cloud REST API v2.0 async client."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from bitbucket_jira_cli.api.base import BaseAsyncClient

BASE_URL = "https://api.bitbucket.org/2.0"


class BitbucketClient(BaseAsyncClient):
    backend = "Bitbucket"

    def __init__(self, authorization: str) -> None:
        super().__init__(BASE_URL, {"Authorization": authorization})

    # -- identity -----------------------------------------------------------
    async def current_user(self) -> dict[str, Any]:
        return await self.get_json("/user")

    # -- repositories -------------------------------------------------------
    async def get_repo(self, workspace: str, repo_slug: str) -> dict[str, Any]:
        return await self.get_json(f"/repositories/{workspace}/{repo_slug}")

    async def list_repos(
        self, workspace: str, *, query: str | None = None, role: str | None = None, limit: int = 30
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"pagelen": min(limit, 100)}
        if query:
            params["q"] = query
        if role:
            params["role"] = role
        return await self._paginate(f"/repositories/{workspace}", params=params, limit=limit)

    async def list_workspace_members(
        self, workspace: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        return await self._paginate(f"/workspaces/{workspace}/members", limit=limit)

    # -- pull requests ------------------------------------------------------
    def _pr_base(self, workspace: str, repo_slug: str) -> str:
        return f"/repositories/{workspace}/{repo_slug}/pullrequests"

    async def create_pr(
        self, workspace: str, repo_slug: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        response = await self.request("POST", self._pr_base(workspace, repo_slug), json=body)
        return response.json()

    async def list_prs(
        self,
        workspace: str,
        repo_slug: str,
        *,
        state: str | None = None,
        source_branch: str | None = None,
        query: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        clauses = []
        if state:
            clauses.append(f'state="{state}"')
        if source_branch:
            clauses.append(f'source.branch.name="{source_branch}"')
        if query:
            clauses.append(query)
        params: dict[str, Any] = {"pagelen": min(limit, 50)}
        if clauses:
            params["q"] = " AND ".join(clauses)
        return await self._paginate(self._pr_base(workspace, repo_slug), params=params, limit=limit)

    async def get_pr(self, workspace: str, repo_slug: str, pr_id: int) -> dict[str, Any]:
        return await self.get_json(f"{self._pr_base(workspace, repo_slug)}/{pr_id}")

    async def update_pr(
        self, workspace: str, repo_slug: str, pr_id: int, body: dict[str, Any]
    ) -> dict[str, Any]:
        response = await self.request(
            "PUT", f"{self._pr_base(workspace, repo_slug)}/{pr_id}", json=body
        )
        return response.json()

    async def merge_pr(
        self, workspace: str, repo_slug: str, pr_id: int, body: dict[str, Any]
    ) -> dict[str, Any]:
        response = await self.request(
            "POST", f"{self._pr_base(workspace, repo_slug)}/{pr_id}/merge", json=body
        )
        return response.json()

    async def decline_pr(self, workspace: str, repo_slug: str, pr_id: int) -> dict[str, Any]:
        response = await self.request(
            "POST", f"{self._pr_base(workspace, repo_slug)}/{pr_id}/decline"
        )
        return response.json()

    async def pr_diff(self, workspace: str, repo_slug: str, pr_id: int) -> str:
        response = await self.request("GET", f"{self._pr_base(workspace, repo_slug)}/{pr_id}/diff")
        return response.text

    async def pr_diffstat(self, workspace: str, repo_slug: str, pr_id: int) -> list[dict[str, Any]]:
        return await self._paginate(
            f"{self._pr_base(workspace, repo_slug)}/{pr_id}/diffstat", params={"pagelen": 100}
        )

    async def approve_pr(self, workspace: str, repo_slug: str, pr_id: int) -> dict[str, Any]:
        response = await self.request(
            "POST", f"{self._pr_base(workspace, repo_slug)}/{pr_id}/approve"
        )
        return response.json()

    async def unapprove_pr(self, workspace: str, repo_slug: str, pr_id: int) -> None:
        await self.request("DELETE", f"{self._pr_base(workspace, repo_slug)}/{pr_id}/approve")

    async def request_changes_pr(
        self, workspace: str, repo_slug: str, pr_id: int
    ) -> dict[str, Any]:
        response = await self.request(
            "POST", f"{self._pr_base(workspace, repo_slug)}/{pr_id}/request-changes"
        )
        return response.json()

    async def list_pr_comments(
        self, workspace: str, repo_slug: str, pr_id: int, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        return await self._paginate(
            f"{self._pr_base(workspace, repo_slug)}/{pr_id}/comments",
            params={"pagelen": 100},
            limit=limit,
        )

    async def add_pr_comment(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
        text: str,
        *,
        inline: dict[str, Any] | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"content": {"raw": text}}
        if inline:
            body["inline"] = inline
        if parent_id is not None:
            body["parent"] = {"id": parent_id}
        response = await self.request(
            "POST", f"{self._pr_base(workspace, repo_slug)}/{pr_id}/comments", json=body
        )
        return response.json()

    def _comment_base(self, workspace: str, repo_slug: str, pr_id: int) -> str:
        return f"{self._pr_base(workspace, repo_slug)}/{pr_id}/comments"

    async def update_pr_comment(
        self, workspace: str, repo_slug: str, pr_id: int, comment_id: int, text: str
    ) -> dict[str, Any]:
        response = await self.request(
            "PUT",
            f"{self._comment_base(workspace, repo_slug, pr_id)}/{comment_id}",
            json={"content": {"raw": text}},
        )
        return response.json()

    async def delete_pr_comment(
        self, workspace: str, repo_slug: str, pr_id: int, comment_id: int
    ) -> None:
        await self.request(
            "DELETE", f"{self._comment_base(workspace, repo_slug, pr_id)}/{comment_id}"
        )

    async def set_pr_comment_resolved(
        self, workspace: str, repo_slug: str, pr_id: int, comment_id: int, *, resolved: bool
    ) -> None:
        method = "POST" if resolved else "DELETE"
        await self.request(
            method, f"{self._comment_base(workspace, repo_slug, pr_id)}/{comment_id}/resolve"
        )

    # -- pull request tasks -------------------------------------------------
    def _task_base(self, workspace: str, repo_slug: str, pr_id: int) -> str:
        return f"{self._pr_base(workspace, repo_slug)}/{pr_id}/tasks"

    async def list_pr_tasks(
        self, workspace: str, repo_slug: str, pr_id: int, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        return await self._paginate(
            self._task_base(workspace, repo_slug, pr_id), params={"pagelen": 100}, limit=limit
        )

    async def add_pr_task(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
        text: str,
        *,
        comment_id: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"content": {"raw": text}}
        if comment_id is not None:
            body["comment"] = {"id": comment_id}
        response = await self.request(
            "POST", self._task_base(workspace, repo_slug, pr_id), json=body
        )
        return response.json()

    async def update_pr_task(
        self,
        workspace: str,
        repo_slug: str,
        pr_id: int,
        task_id: int,
        *,
        state: str | None = None,
        text: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if state is not None:
            body["state"] = state
        if text is not None:
            body["content"] = {"raw": text}
        response = await self.request(
            "PUT", f"{self._task_base(workspace, repo_slug, pr_id)}/{task_id}", json=body
        )
        return response.json()

    async def delete_pr_task(
        self, workspace: str, repo_slug: str, pr_id: int, task_id: int
    ) -> None:
        await self.request(
            "DELETE", f"{self._task_base(workspace, repo_slug, pr_id)}/{task_id}"
        )

    # -- pipelines ----------------------------------------------------------
    def _pipe_base(self, workspace: str, repo_slug: str) -> str:
        return f"/repositories/{workspace}/{repo_slug}/pipelines"

    async def list_pipelines(
        self, workspace: str, repo_slug: str, *, limit: int = 30
    ) -> list[dict[str, Any]]:
        return await self._paginate(
            self._pipe_base(workspace, repo_slug),
            params={"pagelen": min(limit, 50), "sort": "-created_on"},
            limit=limit,
        )

    async def run_pipeline(
        self, workspace: str, repo_slug: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        response = await self.request("POST", self._pipe_base(workspace, repo_slug), json=body)
        return response.json()

    async def get_pipeline(self, workspace: str, repo_slug: str, uuid: str) -> dict[str, Any]:
        return await self.get_json(f"{self._pipe_base(workspace, repo_slug)}/{quote(uuid)}")

    async def stop_pipeline(self, workspace: str, repo_slug: str, uuid: str) -> None:
        await self.request(
            "POST", f"{self._pipe_base(workspace, repo_slug)}/{quote(uuid)}/stopPipeline"
        )

    async def list_pipeline_steps(
        self, workspace: str, repo_slug: str, uuid: str
    ) -> list[dict[str, Any]]:
        return await self._paginate(
            f"{self._pipe_base(workspace, repo_slug)}/{quote(uuid)}/steps", params={"pagelen": 100}
        )

    async def pipeline_step_log(
        self, workspace: str, repo_slug: str, uuid: str, step_uuid: str
    ) -> str:
        response = await self.request(
            "GET",
            f"{self._pipe_base(workspace, repo_slug)}/{quote(uuid)}/steps/{quote(step_uuid)}/log",
        )
        return response.text

    # -- generic passthrough (bj api) --------------------------------------
    async def raw(
        self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None
    ) -> Any:
        response = await self.request(method, path, params=params, json=json)
        try:
            return response.json()
        except ValueError:
            return response.text

    # -- pagination ---------------------------------------------------------
    async def _paginate(
        self, url: str, *, params: dict[str, Any] | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params = params
        while next_url:
            payload = await self.get_json(next_url, params=next_params)
            results.extend(payload.get("values", []))
            if limit is not None and len(results) >= limit:
                return results[:limit]
            next_url = payload.get("next")
            next_params = None  # `next` is an absolute URL with its own query
        return results
