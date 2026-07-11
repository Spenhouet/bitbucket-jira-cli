"""Minimal Atlassian Document Format (ADF) helpers for Jira v3 bodies.

Jira Cloud v3 requires ADF JSON (not plain text/wiki markup) for issue
descriptions and comments. We accept plain text / light Markdown from the user
and emit a valid ADF document: blank-line-separated paragraphs, preserving
hard line breaks within a paragraph.
"""

from __future__ import annotations

from typing import Any


def text_to_adf(text: str) -> dict[str, Any]:
    paragraphs = text.replace("\r\n", "\n").split("\n\n")
    content: list[dict[str, Any]] = []
    for para in paragraphs:
        lines = para.split("\n")
        nodes: list[dict[str, Any]] = []
        for i, line in enumerate(lines):
            if line:
                nodes.append({"type": "text", "text": line})
            if i < len(lines) - 1:
                nodes.append({"type": "hardBreak"})
        content.append({"type": "paragraph", "content": nodes or [{"type": "text", "text": ""}]})
    if not content:
        content = [{"type": "paragraph", "content": []}]
    return {"type": "doc", "version": 1, "content": content}


def adf_to_text(node: Any) -> str:
    """Best-effort flatten of an ADF document back to plain text for display."""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(c) for c in node)
    if not isinstance(node, dict):
        return ""
    node_type = node.get("type")
    if node_type == "text":
        return str(node.get("text", ""))
    if node_type == "hardBreak":
        return "\n"
    children = "".join(adf_to_text(c) for c in node.get("content", []))
    return children + "\n" if node_type == "paragraph" else children
