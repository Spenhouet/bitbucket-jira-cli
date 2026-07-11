"""Tests for the minimal ADF converter used for Jira v3 bodies."""

from bitbucket_jira_cli.api.adf import adf_to_text
from bitbucket_jira_cli.api.adf import text_to_adf


def test_text_to_adf_shape() -> None:
    doc = text_to_adf("hello")
    assert doc["type"] == "doc"
    assert doc["version"] == 1
    assert doc["content"][0]["type"] == "paragraph"


def test_paragraphs_split_on_blank_line() -> None:
    doc = text_to_adf("para1\n\npara2")
    assert len(doc["content"]) == 2


def test_round_trip_preserves_text() -> None:
    text = "line1\nline2\n\npara2"
    out = adf_to_text(text_to_adf(text))
    assert "line1" in out
    assert "para2" in out


def test_empty_text_is_valid_doc() -> None:
    doc = text_to_adf("")
    assert doc["type"] == "doc"
    assert doc["content"]
