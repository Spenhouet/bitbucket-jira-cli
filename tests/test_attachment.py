"""Tests for `bj issue attachment` and binary downloads through the Jira client."""

from pathlib import Path
from typing import Any
from typing import BinaryIO

import httpx
import pytest
from typer.testing import CliRunner

from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.api.jira import JiraClient
from bitbucket_jira_cli.commands import attachment as attachment_cmd
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.config import JiraConfig
from bitbucket_jira_cli.errors import ApiError
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.main import app

runner = CliRunner()

PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(256))
SITE = "https://ex.atlassian.net/rest/api/3"
MEDIA = "https://media.example.test/file/abc/binary"

ATTACHMENTS = [
    {
        "id": "10001",
        "filename": "screenshot.png",
        "size": 2048,
        "mimeType": "image/png",
        "created": "2026-01-01T10:00:00.000+0000",
    },
    {
        "id": "10002",
        "filename": "notes.txt",
        "size": 12,
        "mimeType": "text/plain",
        "created": "2026-01-02T10:00:00.000+0000",
    },
]

CONTENT = {"10001": PNG, "10002": b"hello world\n"}


class FakeJira:
    """Stand-in for JiraClient serving fixed attachments."""

    def __init__(self, attachments: list[dict[str, Any]]) -> None:
        self.attachments = attachments
        self.downloaded: list[str] = []

    async def __aenter__(self) -> "FakeJira":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def list_attachments(self, _key: str) -> list[dict[str, Any]]:
        return self.attachments

    async def download_attachment(self, attachment_id: str, sink: BinaryIO) -> int:
        self.downloaded.append(attachment_id)
        sink.write(CONTENT[attachment_id])
        return len(CONTENT[attachment_id])


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeJira:
    """Point the attachment commands at a fake Jira client."""
    client = FakeJira(ATTACHMENTS)
    config = Config(jira=JiraConfig(site="https://example.atlassian.net"))
    monkeypatch.setattr(attachment_cmd, "load_config", lambda: config)
    monkeypatch.setattr(attachment_cmd, "jira_client", lambda _config: client)
    return client


# -- client --------------------------------------------------------------------
def _client(handler: Any) -> JiraClient:
    client = JiraClient(SITE, "Basic dummy")
    client._client = httpx.AsyncClient(
        base_url=SITE,
        headers={"Authorization": "Basic dummy"},
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    return client


def test_download_follows_redirect_without_leaking_auth(tmp_path: Path) -> None:
    """The content redirect is followed and the media host gets no credentials."""
    seen: list[tuple[str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((str(request.url), request.headers.get("Authorization")))
        if request.url.host == "ex.atlassian.net":
            return httpx.Response(303, headers={"Location": MEDIA})
        return httpx.Response(200, content=PNG, headers={"Content-Type": "image/png"})

    async def _go() -> int:
        async with _client(handler) as client:
            with (tmp_path / "out.png").open("wb") as sink:
                return await client.download_attachment("10001", sink)

    assert run(_go()) == len(PNG)
    assert (tmp_path / "out.png").read_bytes() == PNG
    assert seen == [(f"{SITE}/attachment/content/10001", "Basic dummy"), (MEDIA, None)]


def test_download_error_raises_api_error(tmp_path: Path) -> None:
    """A failed download maps to an ApiError with Jira's message."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"errorMessages": ["Attachment not found"]})

    async def _go() -> None:
        async with _client(handler) as client:
            with (tmp_path / "out.bin").open("wb") as sink:
                await client.download_attachment("1", sink)

    with pytest.raises(ApiError, match="Attachment not found"):
        run(_go())


def test_raw_returns_bytes_for_binary_and_json_for_json() -> None:
    """`raw` keeps binary bodies as bytes and still parses JSON."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/myself"):
            return httpx.Response(200, json={"accountId": "abc"})
        return httpx.Response(200, content=PNG, headers={"Content-Type": "image/png"})

    async def _go(path: str) -> Any:
        async with _client(handler) as client:
            return await client.raw("GET", path)

    assert run(_go("/attachment/content/10001")) == PNG
    assert run(_go("/myself")) == {"accountId": "abc"}


def test_list_attachments_reads_the_attachment_field() -> None:
    """Attachments come from the issue's attachment field."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["fields"] == "attachment"
        return httpx.Response(200, json={"fields": {"attachment": ATTACHMENTS}})

    async def _go() -> list[dict[str, Any]]:
        async with _client(handler) as client:
            return await client.list_attachments("PROJ-1")

    assert run(_go()) == ATTACHMENTS


# -- helpers -------------------------------------------------------------------
@pytest.mark.parametrize(
    ("size", "expected"),
    [(0, "0 B"), (512, "512 B"), (1536, "1.5 KiB"), (2 * 1024**2, "2.0 MiB")],
)
def test_human_size(size: int, expected: str) -> None:
    assert attachment_cmd.human_size(size) == expected


def test_select_attachments_by_name_pattern_and_id() -> None:
    """Filters combine as "any of", and no filter selects everything."""
    select = attachment_cmd.select_attachments
    assert select(ATTACHMENTS, names=[], patterns=[], ids=[]) == ATTACHMENTS
    assert select(ATTACHMENTS, names=["notes.txt"], patterns=[], ids=[]) == [ATTACHMENTS[1]]
    assert select(ATTACHMENTS, names=[], patterns=["*.png"], ids=[]) == [ATTACHMENTS[0]]
    assert select(ATTACHMENTS, names=[], patterns=[], ids=["10002"]) == [ATTACHMENTS[1]]
    assert select(ATTACHMENTS, names=["x"], patterns=["*.txt"], ids=["10001"]) == ATTACHMENTS


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("a.png", "a.png"), ("../../etc/passwd", "passwd"), ("dir\\evil.txt", "evil.txt")],
)
def test_safe_filename_strips_directories(filename: str, expected: str) -> None:
    assert attachment_cmd.safe_filename(filename) == expected


def test_safe_filename_rejects_empty_names() -> None:
    with pytest.raises(BjError, match="not a valid file name"):
        attachment_cmd.safe_filename("..")


# -- commands ------------------------------------------------------------------
@pytest.mark.usefixtures("fake")
def test_list_renders_table() -> None:
    result = runner.invoke(app, ["issue", "attachment", "list", "PROJ-1"])
    assert result.exit_code == 0, result.output
    assert "screenshot.png" in result.output
    assert "2.0 KiB" in result.output
    assert "10002" in result.output


@pytest.mark.usefixtures("fake")
def test_list_json() -> None:
    result = runner.invoke(app, ["issue", "attachment", "list", "PROJ-1", "--json"])
    assert result.exit_code == 0, result.output
    assert '"filename": "notes.txt"' in result.output


def test_list_empty(fake: FakeJira) -> None:
    fake.attachments = []
    result = runner.invoke(app, ["issue", "attachment", "list", "PROJ-1"])
    assert result.exit_code == 0, result.output
    assert "No attachments on PROJ-1" in result.output


@pytest.mark.usefixtures("fake")
def test_download_all_into_dir(tmp_path: Path) -> None:
    """Without filters every attachment is saved under its own name."""
    target = tmp_path / "new" / "dir"
    result = runner.invoke(app, ["issue", "attachment", "download", "PROJ-1", "--dir", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "screenshot.png").read_bytes() == PNG
    assert (target / "notes.txt").read_bytes() == b"hello world\n"
    assert sorted(p.name for p in target.iterdir()) == ["notes.txt", "screenshot.png"]


def test_download_by_pattern(fake: FakeJira, tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["issue", "attachment", "download", "PROJ-1", "-p", "*.png", "-D", str(tmp_path)]
    )
    assert result.exit_code == 0, result.output
    assert fake.downloaded == ["10001"]
    assert [p.name for p in tmp_path.iterdir()] == ["screenshot.png"]


@pytest.mark.usefixtures("fake")
def test_download_to_output_file(tmp_path: Path) -> None:
    out = tmp_path / "renamed.bin"
    result = runner.invoke(
        app, ["issue", "attachment", "download", "PROJ-1", "--id", "10001", "-O", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert out.read_bytes() == PNG


@pytest.mark.usefixtures("fake")
def test_download_to_stdout_keeps_bytes() -> None:
    result = runner.invoke(
        app, ["issue", "attachment", "download", "PROJ-1", "-n", "screenshot.png", "-O", "-"]
    )
    assert result.exit_code == 0, result.output
    assert result.stdout_bytes == PNG


def test_output_needs_a_single_match(fake: FakeJira, tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["issue", "attachment", "download", "PROJ-1", "-O", str(tmp_path / "x")]
    )
    assert isinstance(result.exception, BjError)
    assert "--output takes a single attachment" in str(result.exception)
    assert fake.downloaded == []


@pytest.mark.usefixtures("fake")
def test_no_match_is_an_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["issue", "attachment", "download", "PROJ-1", "-n", "missing.pdf", "-D", str(tmp_path)]
    )
    assert isinstance(result.exception, BjError)
    assert "No matching attachments on PROJ-1" in str(result.exception)


def test_existing_file_is_kept_without_clobber(fake: FakeJira, tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_bytes(b"old")
    result = runner.invoke(app, ["issue", "attachment", "download", "PROJ-1", "-D", str(tmp_path)])
    assert isinstance(result.exception, BjError)
    assert "already exists" in str(result.exception)
    assert (tmp_path / "notes.txt").read_bytes() == b"old"
    assert fake.downloaded == []


def test_skip_existing(fake: FakeJira, tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_bytes(b"old")
    result = runner.invoke(
        app, ["issue", "attachment", "download", "PROJ-1", "-D", str(tmp_path), "--skip-existing"]
    )
    assert result.exit_code == 0, result.output
    assert fake.downloaded == ["10001"]
    assert (tmp_path / "notes.txt").read_bytes() == b"old"


@pytest.mark.usefixtures("fake")
def test_clobber_overwrites(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_bytes(b"old")
    result = runner.invoke(
        app, ["issue", "attachment", "download", "PROJ-1", "-D", str(tmp_path), "--clobber"]
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "notes.txt").read_bytes() == b"hello world\n"
    assert not list(tmp_path.glob("*.part"))


def test_clobber_and_skip_existing_conflict(fake: FakeJira) -> None:
    result = runner.invoke(
        app, ["issue", "attachment", "download", "PROJ-1", "--clobber", "--skip-existing"]
    )
    assert isinstance(result.exception, BjError)
    assert fake.downloaded == []


def test_duplicate_names_need_an_id(fake: FakeJira, tmp_path: Path) -> None:
    """Two attachments with the same name are not silently overwritten."""
    fake.attachments = [*ATTACHMENTS, {**ATTACHMENTS[1], "id": "10003"}]
    result = runner.invoke(app, ["issue", "attachment", "download", "PROJ-1", "-D", str(tmp_path)])
    assert isinstance(result.exception, BjError)
    assert "Several attachments are named 'notes.txt'" in str(result.exception)
    assert fake.downloaded == []
