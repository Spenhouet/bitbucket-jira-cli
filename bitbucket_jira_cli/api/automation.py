"""Jira Cloud Automation REST API async client.

Automation rules live behind their own API, not under ``/rest/api/3``:
``https://api.atlassian.com/automation/public/jira/{cloudId}/rest/v1``.
Atlassian documents basic auth with an (unscoped) API token for it, and the
rule management endpoints need a Jira administrator.
"""

from __future__ import annotations

import copy
from typing import Any
from urllib.parse import parse_qs

import httpx

from bitbucket_jira_cli.api.base import BaseAsyncClient
from bitbucket_jira_cli.errors import ApiError

AUTOMATION_GATEWAY = "https://api.atlassian.com/automation/public/jira"
PAGE_SIZE = 100

# Rule fields the API sets itself; a definition fed to create must not carry them.
READ_ONLY_RULE_FIELDS = ("uuid", "created", "updated")
# Component fields that point at ids of the source rule.
COMPONENT_ID_FIELDS = ("id", "parentId", "conditionParentId")
CONNECTION_WRITE_FIELDS = ("id", "accountId", "connectionTargetKey", "targetConfigJson", "authType")

SCOPE_HINT = (
    "The Automation API rejected the token's scopes. Atlassian documents only "
    "unscoped API tokens for this API; set BJ_JIRA_TOKEN to an unscoped token."
)
ADMIN_HINT = "Managing automation rules needs a Jira administrator."


def automation_base(cloud_id: str) -> str:
    return f"{AUTOMATION_GATEWAY}/{cloud_id}/rest/v1"


def project_scope_ari(cloud_id: str, project_id: str) -> str:
    """The ARI that scopes a rule to one project."""
    return f"ari:cloud:jira:{cloud_id}:project/{project_id}"


def _next_cursor(links: dict[str, Any] | None) -> str | None:
    """Cursor of the next page from ``links.next`` (``?cursor=...&limit=...``)."""
    nxt = (links or {}).get("next")
    if not nxt:
        return None
    query = str(nxt).split("?", 1)[-1]
    values = parse_qs(query).get("cursor")
    return values[0] if values else None


def _strip_component_ids(component: Any) -> None:
    if not isinstance(component, dict):
        return
    for field in COMPONENT_ID_FIELDS:
        component.pop(field, None)
    for key in ("children", "conditions"):
        for child in component.get(key) or []:
            _strip_component_ids(child)


def rule_create_payload(
    definition: dict[str, Any], *, name: str | None = None, enabled: bool = False
) -> dict[str, Any]:
    """Turn an exported rule (``GET /rule/{uuid}``) into a create request body.

    Accepts the full export (``{"rule": ..., "connections": ...}``) or a bare
    rule object. Drops the uuid, timestamps and component ids so the API
    assigns new ones, and sets the state explicitly (disabled by default).
    """
    data = copy.deepcopy(definition)
    rule = data.get("rule") if isinstance(data.get("rule"), dict) else data
    if not isinstance(rule, dict) or "trigger" not in rule:
        msg = "not a rule definition: expected an object with a 'rule' and its 'trigger'"
        raise ValueError(msg)
    for field in READ_ONLY_RULE_FIELDS:
        rule.pop(field, None)
    _strip_component_ids(rule.get("trigger"))
    for component in rule.get("components") or []:
        _strip_component_ids(component)
    if name is not None:
        rule["name"] = name
    rule["state"] = "ENABLED" if enabled else "DISABLED"
    payload: dict[str, Any] = {"rule": rule}
    connections = data.get("connections") if rule is not data else None
    if connections:
        payload["connections"] = [
            {k: v for k, v in conn.items() if k in CONNECTION_WRITE_FIELDS} for conn in connections
        ]
    return payload


class AutomationClient(BaseAsyncClient):
    backend = "Jira Automation"

    def __init__(self, base_url: str, authorization: str) -> None:
        super().__init__(base_url, {"Authorization": authorization})

    def _raise(self, response: httpx.Response) -> None:
        detail = self._automation_error_detail(response)
        if response.status_code == httpx.codes.UNAUTHORIZED and "scope" in detail.lower():
            detail = f"{detail}. {SCOPE_HINT}"
        elif response.status_code == httpx.codes.FORBIDDEN:
            detail = f"{detail}. {ADMIN_HINT}"
        raise ApiError(self.backend, response.status_code, detail)

    @classmethod
    def _automation_error_detail(cls, response: httpx.Response) -> str:
        """Automation errors come as ``{"errors": [{"title", "detail"}]}`` or ``{"message"}``."""
        try:
            body = response.json()
        except ValueError:
            return response.text[:300] or response.reason_phrase
        if isinstance(body, dict):
            errors = body.get("errors")
            if isinstance(errors, list) and errors:
                parts = []
                for err in errors:
                    if isinstance(err, dict):
                        text = err.get("detail") or err.get("title") or err.get("code")
                        parts.append(str(text or err))
                    else:
                        parts.append(str(err))
                return "; ".join(parts)
            if body.get("message"):
                return str(body["message"])
        return cls._error_detail(response)

    # -- rules ----------------------------------------------------------------
    async def list_rules(
        self,
        *,
        state: str | None = None,
        trigger: str | None = None,
        scope: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Rule summaries, following cursors until ``limit`` rules are collected.

        Without filters this is ``GET /rule/summary``; with any filter it is the
        ``POST`` search variant, which takes the cursor in the body.
        """
        filters = {
            k: v for k, v in {"state": state, "trigger": trigger, "scope": scope}.items() if v
        }
        rules: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            page_size = min(limit - len(rules), PAGE_SIZE)
            if filters:
                body: dict[str, Any] = {**filters, "limit": page_size}
                if cursor:
                    body["cursor"] = cursor
                response = await self.request("POST", "/rule/summary", json=body)
                data = response.json()
            else:
                params: dict[str, Any] = {"limit": page_size}
                if cursor:
                    params["cursor"] = cursor
                data = await self.get_json("/rule/summary", params=params)
            rules.extend(data.get("data", []))
            cursor = _next_cursor(data.get("links"))
            if not cursor or len(rules) >= limit:
                break
        return rules[:limit]

    async def get_rule(self, uuid: str) -> dict[str, Any]:
        return await self.get_json(f"/rule/{uuid}")

    async def create_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self.request("POST", "/rule", json=payload)
        return response.json()

    async def set_state(self, uuid: str, state: str) -> None:
        await self.request("PUT", f"/rule/{uuid}/state", json={"value": state})

    async def delete_rule(self, uuid: str) -> None:
        await self.request("DELETE", f"/rule/{uuid}")
