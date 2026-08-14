"""Markdown and Atlassian Document Format (ADF) conversion for Jira v3 bodies.

Jira Cloud v3 takes ADF JSON for issue descriptions and comments, not plain text
and not wiki markup. Bodies are authored as Markdown, so :func:`text_to_adf`
parses them with ``markdown-it-py`` and maps the token stream onto ADF nodes:
headings, paragraphs, bullet and ordered lists, code blocks, block quotes,
rules, tables, and the inline marks (bold, italic, strikethrough, inline code,
links). Plain text is a subset of Markdown and still becomes paragraphs split on
blank lines, with single newlines kept as hard breaks.

:func:`adf_to_text` walks the other way for terminal display, rendering an ADF
document back as Markdown-ish plain text.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from markdown_it import MarkdownIt

if TYPE_CHECKING:
    from collections.abc import Callable

    from markdown_it.token import Token

#: GFM-like enables tables and strikethrough on top of CommonMark.
_PARSER = MarkdownIt("gfm-like")

#: Inline mark per markdown-it tag, for the ``*_open`` / ``*_close`` token pairs.
_MARK_BY_TAG: dict[str, str] = {"strong": "strong", "em": "em", "s": "strike"}


class _Cursor:
    """Cursor over the flat token stream markdown-it produces."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0

    def peek(self) -> Token | None:
        """The next token, or ``None`` at the end of the stream."""
        return self._tokens[self._index] if self._index < len(self._tokens) else None

    def take(self) -> Token:
        """Consume and return the next token."""
        token = self._tokens[self._index]
        self._index += 1
        return token


def text_to_adf(text: str) -> dict[str, Any]:
    """Convert a Markdown body into an ADF document.

    Args:
        text: Markdown source. Plain text is a valid subset.

    Returns:
        An ADF document accepted by the Jira v3 API.
    """
    cursor = _Cursor(_PARSER.parse(text.replace("\r\n", "\n")))
    content = _blocks(cursor)
    return {"type": "doc", "version": 1, "content": content or [_paragraph([])]}


def adf_to_text(node: Any) -> str:
    """Best-effort flatten of an ADF document back to plain text for display.

    Args:
        node: An ADF document, node, list of nodes, or a bare string.

    Returns:
        Markdown-ish plain text.
    """
    return _text(node, 0)


def _paragraph(content: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "paragraph", "content": content}


def _blocks(cursor: _Cursor, stop: str | None = None) -> list[dict[str, Any]]:
    """Convert tokens into block nodes until ``stop`` closes the enclosing node."""
    nodes: list[dict[str, Any]] = []
    while (token := cursor.peek()) is not None:
        if token.type == stop:
            cursor.take()
            break
        node = _block(cursor)
        if node is not None:
            nodes.append(node)
    return nodes


def _block(cursor: _Cursor) -> dict[str, Any] | None:
    """Convert the next block-level token, consuming at least one token."""
    token = cursor.take()
    builder = _BLOCK_BUILDERS.get(token.type)
    return builder(cursor, token) if builder is not None else None


def _paragraph_block(cursor: _Cursor, _token: Token) -> dict[str, Any]:
    return _paragraph(_inline(cursor, "paragraph_close"))


def _heading_block(cursor: _Cursor, token: Token) -> dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": int(token.tag[1:])},
        "content": _inline(cursor, "heading_close"),
    }


def _bullet_list_block(cursor: _Cursor, _token: Token) -> dict[str, Any]:
    return {"type": "bulletList", "content": _list_items(cursor, "bullet_list_close")}


def _ordered_list_block(cursor: _Cursor, token: Token) -> dict[str, Any]:
    start = token.attrGet("start")
    return {
        "type": "orderedList",
        "attrs": {"order": int(start) if start is not None else 1},
        "content": _list_items(cursor, "ordered_list_close"),
    }


def _blockquote_block(cursor: _Cursor, _token: Token) -> dict[str, Any]:
    return {"type": "blockquote", "content": _blocks(cursor, "blockquote_close")}


def _rule_block(_cursor: _Cursor, _token: Token) -> dict[str, Any]:
    return {"type": "rule"}


def _table_block(cursor: _Cursor, _token: Token) -> dict[str, Any]:
    return _table(cursor)


def _literal_block(_cursor: _Cursor, token: Token) -> dict[str, Any] | None:
    """Anything without an ADF counterpart, kept as its own paragraph of text."""
    stripped = token.content.strip()
    return _paragraph([_text_node(stripped, [])]) if stripped else None


def _code_block(_cursor: _Cursor, token: Token) -> dict[str, Any]:
    """A fenced or indented code block, keeping the fence's language when given."""
    node: dict[str, Any] = {"type": "codeBlock"}
    language = token.info.strip().split(" ")[0] if token.info else ""
    if language:
        node["attrs"] = {"language": language}
    code = token.content.rstrip("\n")
    if code:
        node["content"] = [_text_node(code, [])]
    return node


#: Block builder per markdown-it token type. Anything absent is dropped.
_BLOCK_BUILDERS: dict[str, Callable[[_Cursor, Token], dict[str, Any] | None]] = {
    "paragraph_open": _paragraph_block,
    "heading_open": _heading_block,
    "bullet_list_open": _bullet_list_block,
    "ordered_list_open": _ordered_list_block,
    "blockquote_open": _blockquote_block,
    "fence": _code_block,
    "code_block": _code_block,
    "hr": _rule_block,
    "table_open": _table_block,
    "html_block": _literal_block,
    "inline": _literal_block,
    "text": _literal_block,
}


def _list_items(cursor: _Cursor, stop: str) -> list[dict[str, Any]]:
    """The ``listItem`` children of a list, each holding at least one block."""
    items: list[dict[str, Any]] = []
    while (token := cursor.peek()) is not None:
        cursor.take()
        if token.type == stop:
            break
        if token.type == "list_item_open":
            content = _blocks(cursor, "list_item_close")
            items.append({"type": "listItem", "content": content or [_paragraph([])]})
    return items


def _table(cursor: _Cursor) -> dict[str, Any]:
    """A table, flattening the ``thead`` and ``tbody`` grouping ADF does not have."""
    rows: list[dict[str, Any]] = []
    while (token := cursor.peek()) is not None:
        cursor.take()
        if token.type == "table_close":
            break
        if token.type == "tr_open":
            rows.append({"type": "tableRow", "content": _table_cells(cursor)})
    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": rows,
    }


def _table_cells(cursor: _Cursor) -> list[dict[str, Any]]:
    """The cells of one table row."""
    cells: list[dict[str, Any]] = []
    while (token := cursor.peek()) is not None:
        cursor.take()
        if token.type == "tr_close":
            break
        if token.type in {"th_open", "td_open"}:
            kind = "tableHeader" if token.type == "th_open" else "tableCell"
            content = _inline(cursor, "th_close" if token.type == "th_open" else "td_close")
            cells.append({"type": kind, "attrs": {}, "content": [_paragraph(content)]})
    return cells


def _inline(cursor: _Cursor, stop: str) -> list[dict[str, Any]]:
    """Convert the inline token of the current block into text nodes."""
    nodes: list[dict[str, Any]] = []
    while (token := cursor.peek()) is not None:
        cursor.take()
        if token.type == stop:
            break
        if token.type == "inline":
            nodes.extend(_inline_nodes(token.children or []))
    return nodes


def _inline_nodes(children: list[Token]) -> list[dict[str, Any]]:
    """Flatten inline tokens into ADF text nodes, carrying the open marks."""
    nodes: list[dict[str, Any]] = []
    marks: list[dict[str, Any]] = []
    for child in children:
        if child.type in {"text", "html_inline"}:
            _append(nodes, child.content, marks)
        elif child.type == "code_inline":
            _append(nodes, child.content, [*marks, {"type": "code"}])
        elif child.type in {"softbreak", "hardbreak"}:
            nodes.append({"type": "hardBreak"})
        elif child.type == "image":
            _append_image(nodes, child, marks)
        elif child.type == "link_open":
            marks.append(_link(str(child.attrGet("href") or "")))
        elif child.type.endswith("_open") and child.tag in _MARK_BY_TAG:
            marks.append({"type": _MARK_BY_TAG[child.tag]})
        elif child.type.endswith("_close") and marks:
            marks.pop()
    return nodes


def _append_image(nodes: list[dict[str, Any]], token: Token, marks: list[dict[str, Any]]) -> None:
    """Render an image as a link, since ADF media needs an uploaded attachment id."""
    source = str(token.attrGet("src") or "")
    label = token.content or source
    _append(nodes, label, [*marks, _link(source)] if source else marks)


def _append(nodes: list[dict[str, Any]], text: str, marks: list[dict[str, Any]]) -> None:
    """Append a text node, skipping empty text which ADF rejects."""
    if text:
        nodes.append(_text_node(text, marks))


def _text_node(text: str, marks: list[dict[str, Any]]) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "text", "text": text}
    if marks:
        node["marks"] = [dict(mark) for mark in marks]
    return node


def _link(href: str) -> dict[str, Any]:
    return {"type": "link", "attrs": {"href": href}}


def _text(node: Any, depth: int) -> str:
    """Render a node back to plain text, indenting nested lists by ``depth``."""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_text(child, depth) for child in node)
    if not isinstance(node, dict):
        return ""
    renderer = _TEXT_RENDERERS.get(str(node.get("type")))
    return renderer(node, depth) if renderer is not None else _children(node, depth)


def _leaf_text(node: dict[str, Any], _depth: int) -> str:
    return str(node.get("text", ""))


def _break_text(_node: dict[str, Any], _depth: int) -> str:
    return "\n"


def _rule_text(_node: dict[str, Any], _depth: int) -> str:
    return "---\n"


def _heading_text(node: dict[str, Any], depth: int) -> str:
    level = int((node.get("attrs") or {}).get("level", 1))
    return f"{'#' * level} {_children(node, depth).strip()}\n"


def _paragraph_text(node: dict[str, Any], depth: int) -> str:
    return _children(node, depth) + "\n"


def _code_text(node: dict[str, Any], depth: int) -> str:
    language = str((node.get("attrs") or {}).get("language", ""))
    return f"```{language}\n{_children(node, depth).rstrip()}\n```\n"


def _quote_text(node: dict[str, Any], depth: int) -> str:
    inner = _children(node, depth).rstrip("\n")
    return "".join(f"> {line}\n" for line in inner.split("\n"))


def _row_text(node: dict[str, Any], depth: int) -> str:
    return " | ".join(_text(cell, depth).strip() for cell in node.get("content", [])) + "\n"


def _list_text(node: dict[str, Any], depth: int) -> str:
    """Render a list, one line per item, ordered lists numbered from their start."""
    start = int((node.get("attrs") or {}).get("order", 1))
    numbered = node.get("type") == "orderedList"
    indent = "  " * depth
    lines: list[str] = []
    for offset, item in enumerate(node.get("content", [])):
        marker = f"{start + offset}." if numbered else "-"
        first, *rest = _text(item, depth + 1).rstrip("\n").split("\n")
        lines.append(f"{indent}{marker} {first}\n")
        lines.extend(f"{line}\n" for line in rest)
    return "".join(lines)


def _children(node: dict[str, Any], depth: int) -> str:
    return "".join(_text(child, depth) for child in node.get("content", []))


#: Plain-text renderer per ADF node type. Anything absent renders its children.
_TEXT_RENDERERS: dict[str, Callable[[dict[str, Any], int], str]] = {
    "text": _leaf_text,
    "hardBreak": _break_text,
    "rule": _rule_text,
    "heading": _heading_text,
    "paragraph": _paragraph_text,
    "codeBlock": _code_text,
    "blockquote": _quote_text,
    "bulletList": _list_text,
    "orderedList": _list_text,
    "tableRow": _row_text,
}
