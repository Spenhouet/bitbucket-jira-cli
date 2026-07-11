"""Shared async client plumbing: request, error mapping, JSON helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import httpx

from bitbucket_jira_cli.errors import ApiError

if TYPE_CHECKING:
    from types import TracebackType

DEFAULT_TIMEOUT = 30.0


class BaseAsyncClient:
    """Thin wrapper over ``httpx.AsyncClient`` with error mapping.

    Subclasses set ``backend`` (for error messages) and pass a base URL and
    default headers (including ``Authorization``).
    """

    backend = "api"

    def __init__(self, base_url: str, headers: dict[str, str]) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Accept": "application/json", **headers},
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
        )

    async def __aenter__(self) -> BaseAsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _raise(self, response: httpx.Response) -> None:
        detail = self._error_detail(response)
        raise ApiError(self.backend, response.status_code, detail)

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:300] or response.reason_phrase
        # Bitbucket: {"error": {"message": ...}}; Jira: {"errorMessages": [...]}
        if isinstance(body, dict):
            if isinstance(body.get("error"), dict) and body["error"].get("message"):
                return str(body["error"]["message"])
            if body.get("errorMessages"):
                return "; ".join(body["errorMessages"])
            if body.get("errors"):
                return "; ".join(f"{k}: {v}" for k, v in body["errors"].items())
        return response.text[:300] or response.reason_phrase

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        content: bytes | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        response = await self._client.request(
            method, url, params=params, json=json, content=content, headers=headers
        )
        if response.status_code >= httpx.codes.BAD_REQUEST:
            self._raise(response)
        return response

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        response = await self.request("GET", url, params=params)
        return response.json()
