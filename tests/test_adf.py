"""Tests for the Markdown to ADF converter used for Jira v3 bodies."""

from typing import Any

import pytest

from bitbucket_jira_cli.api.adf import adf_to_text
from bitbucket_jira_cli.api.adf import text_to_adf


def _first(doc: dict[str, Any]) -> dict[str, Any]:
    return doc["content"][0]


def _flatten(node: Any) -> list[dict[str, Any]]:
    """Every node of a document, depth first."""
    if isinstance(node, list):
        return [item for child in node for item in _flatten(child)]
    if not isinstance(node, dict):
        return []
    return [node, *_flatten(node.get("content", []))]


def test_text_to_adf_shape() -> None:
    doc = text_to_adf("hello")
    assert doc["type"] == "doc"
    assert doc["version"] == 1
    assert _first(doc)["type"] == "paragraph"


def test_paragraphs_split_on_blank_line() -> None:
    doc = text_to_adf("para1\n\npara2")
    assert len(doc["content"]) == 2


def test_single_newline_becomes_hard_break() -> None:
    doc = text_to_adf("line1\nline2")
    types = [node["type"] for node in _first(doc)["content"]]
    assert types == ["text", "hardBreak", "text"]


def test_round_trip_preserves_text() -> None:
    text = "line1\nline2\n\npara2"
    out = adf_to_text(text_to_adf(text))
    assert "line1" in out
    assert "para2" in out


def test_empty_text_is_valid_doc() -> None:
    doc = text_to_adf("")
    assert doc["type"] == "doc"
    assert doc["content"]


@pytest.mark.parametrize(("source", "level"), [("# One", 1), ("### Three", 3)])
def test_heading_carries_its_level(source: str, level: int) -> None:
    node = _first(text_to_adf(source))
    assert node["type"] == "heading"
    assert node["attrs"]["level"] == level


def test_bullet_list_becomes_list_items() -> None:
    node = _first(text_to_adf("- one\n- two"))
    assert node["type"] == "bulletList"
    assert [item["type"] for item in node["content"]] == ["listItem", "listItem"]


def test_nested_bullet_list_nests_in_its_item() -> None:
    node = _first(text_to_adf("- outer\n    - inner"))
    inner = node["content"][0]["content"][1]
    assert inner["type"] == "bulletList"
    assert adf_to_text(inner["content"][0]).strip() == "inner"


def test_ordered_list_keeps_its_start() -> None:
    node = _first(text_to_adf("3. three\n4. four"))
    assert node["type"] == "orderedList"
    assert node["attrs"]["order"] == 3


def test_fenced_code_block_keeps_language_and_body() -> None:
    node = _first(text_to_adf("```python\nx = 1\n```"))
    assert node["type"] == "codeBlock"
    assert node["attrs"]["language"] == "python"
    assert node["content"][0]["text"] == "x = 1"


def test_fence_without_language_has_no_attrs() -> None:
    node = _first(text_to_adf("```\nplain\n```"))
    assert "attrs" not in node


@pytest.mark.parametrize(
    ("source", "mark"),
    [("**bold**", "strong"), ("*italic*", "em"), ("~~gone~~", "strike"), ("`code`", "code")],
)
def test_inline_marks(source: str, mark: str) -> None:
    node = _first(text_to_adf(source))["content"][0]
    assert [entry["type"] for entry in node["marks"]] == [mark]


def test_link_becomes_a_link_mark() -> None:
    node = _first(text_to_adf("see [docs](https://example.com)"))["content"][1]
    assert node["marks"][0] == {"type": "link", "attrs": {"href": "https://example.com"}}


def test_marks_do_not_leak_past_their_closing_token() -> None:
    nodes = _first(text_to_adf("**bold** plain"))["content"]
    assert "marks" not in nodes[1]


def test_blockquote_wraps_its_paragraph() -> None:
    node = _first(text_to_adf("> quoted"))
    assert node["type"] == "blockquote"
    assert node["content"][0]["type"] == "paragraph"


def test_thematic_break_becomes_a_rule() -> None:
    assert _first(text_to_adf("---"))["type"] == "rule"


def test_table_rows_use_header_and_cell_nodes() -> None:
    node = _first(text_to_adf("| a | b |\n| --- | --- |\n| 1 | 2 |"))
    assert node["type"] == "table"
    header, body = node["content"]
    assert [cell["type"] for cell in header["content"]] == ["tableHeader", "tableHeader"]
    assert [cell["type"] for cell in body["content"]] == ["tableCell", "tableCell"]


def test_no_empty_text_nodes() -> None:
    doc = text_to_adf("# head\n\n- item\n\n```\n\n```\n\n| a |\n| - |\n|  |")
    assert all(node["text"] for node in _flatten(doc) if node.get("type") == "text")


def test_list_items_always_hold_a_block() -> None:
    doc = text_to_adf("-\n- filled")
    items = [node for node in _flatten(doc) if node.get("type") == "listItem"]
    assert all(item["content"] for item in items)


def test_adf_to_text_renders_block_structure() -> None:
    out = adf_to_text(text_to_adf("## Title\n\n- one\n- two\n\n```sh\nls\n```"))
    assert "## Title" in out
    assert "- one" in out
    assert "```sh" in out


def test_adf_to_text_numbers_ordered_items() -> None:
    out = adf_to_text(text_to_adf("2. two\n3. three"))
    assert out.splitlines() == ["2. two", "3. three"]


def test_adf_to_text_accepts_a_bare_string() -> None:
    assert adf_to_text("plain") == "plain"
