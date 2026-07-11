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


def is_user_type(schema: dict[str, Any]) -> bool:
    return schema.get("type") == "user" or (
        schema.get("type") == "array" and schema.get("items") == "user"
    )


def coerce_value(raw: str, meta: dict[str, Any]) -> Any:  # noqa: PLR0911
    """Coerce a user-typed string to the JSON shape the field expects (non-user).

    User-typed fields are resolved separately (they need an async accountId lookup).
    """
    schema = meta.get("schema", {})
    allowed = meta.get("allowedValues", [])
    field_type = schema.get("type")
    if field_type == "number":
        return float(raw) if "." in raw else int(raw)
    if field_type in ("string", "date", "datetime"):
        return raw
    if field_type == "option":
        return _option(raw, allowed)
    if field_type in ("priority", "version", "component", "resolution", "project"):
        return {"name": raw}
    if field_type == "array":
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        items = schema.get("items")
        if items == "option":
            return [_option(p, allowed) for p in parts]
        return parts  # array of strings (e.g. labels)
    # Unknown/complex type: accept literal JSON, else send the raw string.
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw
