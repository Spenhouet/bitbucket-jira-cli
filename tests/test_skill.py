"""Tests for `bj skill install` (the bundled agent skill installer)."""

from pathlib import Path

import yaml
from typer.testing import CliRunner

from bitbucket_jira_cli.commands.skill import _resolve_dir
from bitbucket_jira_cli.commands.skill import _skill_source
from bitbucket_jira_cli.commands.skill import _with_provenance
from bitbucket_jira_cli.main import app

runner = CliRunner()


def test_skill_source_has_expected_frontmatter() -> None:
    """The bundled skill is discoverable and names itself correctly."""
    text = _skill_source()
    assert text.startswith("---")
    front = yaml.safe_load(text.split("---", 2)[1])
    assert front["name"] == "bitbucket-jira-cli"
    assert "gh" in front["description"]


def test_print_writes_skill_to_stdout() -> None:
    """`--print` emits the SKILL.md without touching the filesystem."""
    result = runner.invoke(app, ["skill", "install", "--print"])
    assert result.exit_code == 0
    assert "name: bitbucket-jira-cli" in result.stdout


def test_install_to_dir_injects_provenance(tmp_path: Path) -> None:
    """Installing writes SKILL.md with source-tracking metadata in frontmatter."""
    result = runner.invoke(app, ["skill", "install", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    dest = tmp_path / "bitbucket-jira-cli" / "SKILL.md"
    assert dest.is_file()
    front = yaml.safe_load(dest.read_text(encoding="utf-8").split("---", 2)[1])
    assert front["metadata"]["source"] == "bitbucket-jira-cli"
    assert "version" in front["metadata"]


def test_overwrite_needs_force(tmp_path: Path) -> None:
    """A second install fails without --force, then succeeds with it."""
    args = ["skill", "install", "--dir", str(tmp_path)]
    assert runner.invoke(app, args).exit_code == 0
    assert runner.invoke(app, args).exit_code == 1  # exists, non-interactive, no --force
    assert runner.invoke(app, [*args, "--force"]).exit_code == 0


def test_bad_scope_errors(tmp_path: Path) -> None:
    """An invalid --scope is rejected."""
    result = runner.invoke(app, ["skill", "install", "--scope", "bogus", "--dir", str(tmp_path)])
    assert result.exit_code == 1


def test_resolve_dir_conventions(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """Agent/scope map to the gh-style skill directories."""
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: tmp_path))
    assert _resolve_dir("claude-code", "user") == tmp_path / ".claude/skills"
    assert _resolve_dir("github-copilot", "user") == tmp_path / ".copilot/skills"
    # Unknown agents share the generic .agents/skills directory.
    assert _resolve_dir("cursor", "user") == tmp_path / ".agents/skills"


def test_with_provenance_is_idempotent_shape() -> None:
    """Provenance injection keeps a valid single frontmatter block."""
    out = _with_provenance(_skill_source())
    assert out.count("---") >= 2
    front = yaml.safe_load(out.split("---", 2)[1])
    assert front["name"] == "bitbucket-jira-cli"
    assert front["metadata"]["source"] == "bitbucket-jira-cli"
