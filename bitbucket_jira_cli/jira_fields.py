"""Resolve and coerce Jira fields from a per-issue editmeta.

editmeta (``GET /issue/{key}/editmeta``) is the source of truth for what is
editable on a specific issue and each field's schema/allowedValues — so `bj` can
set arbitrary custom fields with no per-field configuration, coercing the string
the user typed into the shape the field's ``schema.type`` requires.
"""

from __future__ import annotations

import json
from typing import Any

from bitbucket_jira_cli.errors import BjError


def _norm(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def build_index(editmeta: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    """Map field id, display name, and hyphenated name → (field_id, field_meta)."""
    index: dict[str, tuple[str, dict[str, Any]]] = {}
    for field_id, meta in editmeta.items():
        entry = (field_id, meta)
        index[field_id.lower()] = entry
        name = meta.get("name", "")
        if name:
            index[name.lower()] = entry
            index[_norm(name)] = entry
    return index


def resolve_field(
    name: str, index: dict[str, tuple[str, dict[str, Any]]]
) -> tuple[str, dict[str, Any]]:
    for key in (name.lower(), _norm(name)):
        if key in index:
            return index[key]
    msg = f"Field '{name}' is not editable on this issue (not on its edit screen)."
    raise BjError(msg)


def _option(value: str, allowed: list[dict[str, Any]]) -> dict[str, str]:
    for opt in allowed:
        if str(opt.get("value", "")).lower() == value.lower():
            return {"value": opt["value"]}
        if str(opt.get("id", "")) == value:
            return {"id": str(opt["id"])}
    # Not in allowedValues (or none provided) — send as a plain value.
    return {"value": value}


def _issue_link(raw: str) -> Any:
    """Reference another issue by key or id, which the API takes as an object."""
    text = raw.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except ValueError:
            pass
    return {"id": text} if text.isdigit() else {"key": text}


# Types the API identifies by name inside an object, e.g. {"name": "v1.2.0"}.
_NAMED_TYPES = frozenset({"priority", "version", "component", "resolution", "project", "group"})
# Types that travel as the plain string the user typed.
_TEXT_TYPES = frozenset({"string", "date", "datetime"})
_KNOWN_TYPES = _NAMED_TYPES | _TEXT_TYPES | {"number", "option", "issuelink"}


def _coerce_one(raw: str, field_type: str | None, allowed: list[dict[str, Any]]) -> Any:
    """Coerce one value, whether it is a whole field or a single array element."""
    if field_type == "number":
        return float(raw) if "." in raw else int(raw)
    if field_type == "option":
        return _option(raw, allowed)
    if field_type == "issuelink":
        return _issue_link(raw)
    if field_type in _NAMED_TYPES:
        return {"name": raw}
    return raw


def is_user_type(schema: dict[str, Any]) -> bool:
    return schema.get("type") == "user" or (
        schema.get("type") == "array" and schema.get("items") == "user"
    )


def coerce_value(raw: str, meta: dict[str, Any]) -> Any:
    """Coerce a user-typed string to the JSON shape the field expects (non-user).

    An array field takes a comma-separated list and coerces every element by the
    field's ``schema.items``, so ``Fix versions=v1.2.0, v1.3.0`` reaches the API as
    version objects rather than as bare strings.

    User-typed fields are resolved separately (they need an async accountId lookup).
    """
    schema = meta.get("schema", {})
    allowed = meta.get("allowedValues", [])
    field_type = schema.get("type")
    if field_type == "array":
        item_type = schema.get("items")
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        return [_coerce_one(p, item_type, allowed) for p in parts]
    if field_type in _KNOWN_TYPES:
        return _coerce_one(raw, field_type, allowed)
    # Unknown/complex type: accept literal JSON, else send the raw string.
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw
