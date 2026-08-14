"""Tests for resolving and coercing Jira fields from a per-issue editmeta."""

from typing import Any

import pytest

from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.jira_fields import build_index
from bitbucket_jira_cli.jira_fields import coerce_value
from bitbucket_jira_cli.jira_fields import is_user_type
from bitbucket_jira_cli.jira_fields import resolve_field

_EDITMETA: dict[str, Any] = {
    "parent": {"name": "Parent", "schema": {"type": "issuelink", "system": "parent"}},
    "customfield_10016": {"name": "Story Points", "schema": {"type": "number"}},
    "labels": {"name": "Labels", "schema": {"type": "array", "items": "string"}},
}


def _meta(field_type: str, **schema: Any) -> dict[str, Any]:
    return {"schema": {"type": field_type, **schema}}


@pytest.mark.parametrize("name", ["parent", "Parent", "PARENT"])
def test_resolve_field_by_id_or_name(name: str) -> None:
    field_id, _ = resolve_field(name, build_index(_EDITMETA))
    assert field_id == "parent"


def test_resolve_field_by_hyphenated_name() -> None:
    field_id, _ = resolve_field("story-points", build_index(_EDITMETA))
    assert field_id == "customfield_10016"


def test_resolve_field_rejects_unknown_name() -> None:
    with pytest.raises(BjError, match="not editable"):
        resolve_field("Sprint", build_index(_EDITMETA))


def test_issue_link_wraps_a_bare_key() -> None:
    assert coerce_value("PROJ-1", _meta("issuelink")) == {"key": "PROJ-1"}


def test_issue_link_treats_digits_as_an_id() -> None:
    assert coerce_value("10023", _meta("issuelink")) == {"id": "10023"}


def test_issue_link_keeps_an_explicit_object() -> None:
    assert coerce_value('{"key": "PROJ-2"}', _meta("issuelink")) == {"key": "PROJ-2"}


def test_issue_link_falls_back_on_malformed_json() -> None:
    assert coerce_value('{"key"', _meta("issuelink")) == {"key": '{"key"'}


@pytest.mark.parametrize(("raw", "expected"), [("3", 3), ("2.5", 2.5)])
def test_number_keeps_its_kind(raw: str, expected: float) -> None:
    assert coerce_value(raw, _meta("number")) == expected


def test_array_of_strings_splits_on_commas() -> None:
    assert coerce_value("a, b", _meta("array", items="string")) == ["a", "b"]


def test_option_matches_an_allowed_value() -> None:
    meta = {**_meta("option"), "allowedValues": [{"value": "High", "id": "1"}]}
    assert coerce_value("high", meta) == {"value": "High"}


def test_unknown_type_passes_the_raw_string() -> None:
    assert coerce_value("anything", _meta("mystery")) == "anything"


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"type": "user"}, True),
        ({"type": "array", "items": "user"}, True),
        ({"type": "array", "items": "string"}, False),
        ({"type": "string"}, False),
    ],
)
def test_is_user_type(schema: dict[str, Any], expected: bool) -> None:
    assert is_user_type(schema) is expected
