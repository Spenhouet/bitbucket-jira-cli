"""`bj skill` - install the bundled agent skill (mirrors `gh skill install`).

`bj` ships an Agent Skill (a ``SKILL.md`` playbook) that teaches AI coding
agents how to drive `bj`. This command copies it into an agent's skills
directory, the same way ``gh skill install`` distributes skills, but from the
package you already installed rather than from a remote repository.
"""

from __future__ import annotations

import importlib.resources
import sys
from pathlib import Path
from typing import Annotated

import typer
import yaml

from bitbucket_jira_cli import __version__
from bitbucket_jira_cli.errors import BjError
from bitbucket_jira_cli.interaction import confirm
from bitbucket_jira_cli.interaction import is_interactive
from bitbucket_jira_cli.interaction import select
from bitbucket_jira_cli.ui import console
from bitbucket_jira_cli.ui import success

skill_app = typer.Typer(
    name="skill",
    help="Install the bj agent skill into a coding agent (mirrors `gh skill`).",
    no_args_is_help=True,
)

SKILL_NAME = "bitbucket-jira-cli"

# Agent -> (project-scope dir, user-scope dir), relative to the repo root / home.
# Mirrors the directory conventions used by `gh skill install`: most agents share
# `.agents/skills`; Claude Code and Copilot have their own product directories.
_AGENT_DIRS: dict[str, tuple[str, str]] = {
    "claude-code": (".claude/skills", ".claude/skills"),
    "github-copilot": (".github/skills", ".copilot/skills"),
}
_SHARED_DIRS = (".agents/skills", ".agents/skills")

# Offered when picking interactively; any other `--agent` value is accepted and
# routed to the shared `.agents/skills` directory (as `gh skill` does).
_AGENT_CHOICES = ["claude-code", "github-copilot", "other (.agents/skills)"]
_DEFAULT_AGENT = "github-copilot"  # gh's non-interactive default


def _skill_source() -> str:
    """Return the bundled ``SKILL.md`` text (installed wheel or source tree)."""
    packaged = importlib.resources.files("bitbucket_jira_cli").joinpath("_skill/SKILL.md")
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    # Running from a source checkout: the skill lives at the repo root.
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "skills" / SKILL_NAME / "SKILL.md"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    msg = "bundled skill not found; reinstall bitbucket-jira-cli"
    raise BjError(msg)


def _with_provenance(text: str) -> str:
    """Inject source-tracking metadata into the skill frontmatter, like `gh skill`."""
    if not text.startswith("---"):
        return text
    _, front, body = text.split("---", 2)
    meta = yaml.safe_load(front) or {}
    meta["metadata"] = {"source": SKILL_NAME, "version": __version__}
    dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=10**6).strip()
    return f"---\n{dumped}\n---{body}"


def _project_root() -> Path:
    """The current git repository root, or the working directory if not in one."""
    cwd = Path.cwd()
    for path in (cwd, *cwd.parents):
        if (path / ".git").exists():
            return path
    return cwd


def _resolve_dir(agent: str, scope: str) -> Path:
    project, user = _AGENT_DIRS.get(agent, _SHARED_DIRS)
    if scope == "user":
        return Path.home() / user
    return _project_root() / project


@skill_app.command("install")
def install(
    agent: Annotated[
        str | None,
        typer.Option("--agent", "-a", help="Target agent (e.g. claude-code, github-copilot)."),
    ] = None,
    scope: Annotated[
        str, typer.Option("--scope", "-s", help="Install location: 'project' or 'user'.")
    ] = "project",
    directory: Annotated[
        Path | None,
        typer.Option("--dir", "-d", help="Custom directory (overrides --agent and --scope)."),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite an existing skill without asking.")
    ] = False,
    print_only: Annotated[
        bool, typer.Option("--print", help="Write the SKILL.md to stdout instead of installing.")
    ] = False,
) -> None:
    """Install the bj agent skill so coding agents know how to drive `bj`."""
    source = _skill_source()

    if print_only:
        sys.stdout.write(source if source.endswith("\n") else source + "\n")
        return

    if scope not in ("project", "user"):
        msg = "--scope must be 'project' or 'user'."
        raise BjError(msg)

    if directory is not None:
        target_dir = directory
    else:
        chosen = agent
        if chosen is None:
            chosen = (
                select("Install the skill for which agent?", _AGENT_CHOICES).split(" ")[0]
                if is_interactive()
                else _DEFAULT_AGENT
            )
        # An unmapped agent (or the "other" pick) lands in the shared directory.
        target_dir = _resolve_dir(chosen, scope)

    dest = target_dir / SKILL_NAME / "SKILL.md"
    if dest.exists() and not force:
        # Mirror `gh skill install`: overwriting needs -f, or a yes in an
        # interactive session. Never overwrite silently when non-interactive.
        if not is_interactive() or not confirm(
            f"{dest} exists. Overwrite?", yes=False, default=False
        ):
            msg = f"{dest} already exists; pass --force to overwrite."
            raise BjError(msg)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_with_provenance(source), encoding="utf-8")
    success(f"Installed skill '{SKILL_NAME}' to {dest}")
    console.print(
        "[dim]Restart your agent (or reload skills) to pick it up. "
        "Verify with `bj skill install --print`.[/dim]"
    )
