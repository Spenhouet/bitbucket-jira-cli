#!/usr/bin/env python
"""Generate the Docusaurus command reference from the live Typer command tree.

Mirrors how `gh`'s manual is generated from its Cobra tree: one page per command
and per subcommand, each with the same skeleton (title, one-line description,
synopsis, description, arguments, options, examples, see also). Run:

    uv run python scripts/gen_cli_docs.py

Output goes to docs/reference/ (wiped and regenerated each run). Pages are
CommonMark (.md) so API notation like {workspace} and <key> is literal; the
site is configured with `markdown.format: "detect"`.

Typer vendors click, so the command objects are duck-typed (they expose the
usual click attributes: .commands, .params, .param_type_name, .opts, …).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import typer

from bitbucket_jira_cli.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "docs" / "reference"
SHORT_OPT_LEN = 2  # a short flag is like "-t"

# Command grouping on the reference landing page (mirrors gh's Core/Actions/…).
GROUPS: list[tuple[str, list[str]]] = [
    ("Core commands", ["auth", "repo", "pr", "issue"]),
    ("Jira planning", ["release", "board"]),
    ("Pipelines", ["pipeline", "variable"]),
    ("Search and status", ["search", "status"]),
    ("Configuration", ["config", "alias", "ssh-key"]),
    ("Utility", ["skill", "snippet", "ruleset", "browse", "api"]),
]

# Extended descriptions for the commands that warrant more than the one-liner.
DESCRIPTIONS: dict[str, str] = {
    "": (
        "`bj` brings the ergonomics of GitHub's `gh` CLI to Bitbucket Cloud and "
        "Jira Cloud. It manages Bitbucket pull requests, repositories and "
        "pipelines and Jira issues from a single noun-first command surface, and "
        "reads the Jira key from your git branch to auto-link and transition "
        "tickets. See the [branch-key workflow](../guides/branch-key.md) guide."
    ),
    "auth": (
        "`bj` stores two independent credentials, one for Bitbucket and one for "
        "Jira, because the two products use separate API tokens. Tokens go to "
        "the OS keyring by default, or a 0600 file with `--insecure-storage`. "
        "See the [environment](../../guides/environment.md) guide for the "
        "`BJ_*_TOKEN` overrides."
    ),
    "pr create": (
        "Open a pull request for the current branch. When the branch name "
        "carries a Jira key (e.g. `feature/PROJ-42-thing`), `bj` fills the title "
        "from the ticket, links the PR to the issue, and transitions the ticket "
        "to the configured in-progress state. Use `--no-jira` to skip that, or "
        "`--dry-run` to preview without writing. See "
        "[branch-key workflow](../../guides/branch-key.md)."
    ),
    "pr merge": (
        "Merge a pull request. If the PR's branch carries a Jira key, the linked "
        "ticket is transitioned to the configured done state on success."
    ),
    "issue view": (
        "View a Jira issue. With no key, the key is read from the current git "
        "branch name."
    ),
    "api": (
        "Make an authenticated request against the Bitbucket or Jira REST API and "
        "print the JSON response. Choose the backend with `--backend`; `--field` "
        "adds parameters (query string for GET, JSON body otherwise)."
    ),
    "browse": (
        "Open the repository, the current branch's pull request, or the branch's "
        "Jira issue in your browser. Use `--no-browser` to print the URL instead."
    ),
    "skill": (
        "`bj` ships an [Agent Skill](https://agentskills.io/): a `SKILL.md` "
        "playbook that teaches AI coding agents how to drive `bj`. This mirrors "
        "`gh skill`, but installs the skill bundled with the package rather than "
        "fetching it from a remote repository. See the "
        "[coding agents](../../guides/agents.md) guide."
    ),
    "release": (
        "Jira project versions, the analog of GitHub releases. A version is a "
        "named milestone that issues target with their fix version and that you "
        "eventually mark released."
    ),
    "variable": (
        "Bitbucket Pipelines variables. Bitbucket models secrets and plaintext "
        "variables as one resource with a `secured` flag, so `--secured` covers "
        "what `gh secret` does."
    ),
    "config": (
        "Read and write non-sensitive settings in `config.yml` using dotted keys "
        "(e.g. `bitbucket.workspace`). Values are validated against the schema."
    ),
    "search": (
        "Search Bitbucket repositories and code and Jira issues (JQL). Jira issue "
        "search is also available as `bj issue list --jql`."
    ),
    "status": (
        "A dashboard of what needs your attention: open Jira issues assigned to "
        "you and open pull requests in the current repository."
    ),
    "alias": (
        "User-defined command shortcuts, stored in `config.yml` and expanded "
        "before dispatch. `bj alias set co 'pr checkout'` makes `bj co` work."
    ),
    "ssh-key": (
        "Manage your Bitbucket account SSH keys. Needs a token with account "
        "scope; the default login scopes do not include it."
    ),
    "skill install": (
        "Copy the bundled agent skill into an agent's skills directory. The "
        "target follows the same conventions as `gh skill install`: `--scope "
        "project` (default) writes into the current repository, `--scope user` "
        "into your home directory, and `--agent` selects the directory "
        "(`claude-code` uses `.claude/skills`, others share `.agents/skills`). "
        "`--print` writes the `SKILL.md` to stdout instead."
    ),
}

# Curated examples per command (gh-style: real invocations, a few variations).
EXAMPLES: dict[str, list[str]] = {
    "auth login": [
        "# Log in to both backends interactively",
        "bj auth login",
        "",
        "# Only Jira; read the token from stdin (non-interactive)",
        'printf "%s" "$JIRA_TOKEN" | bj auth login --jira --with-token',
    ],
    "auth status": ["bj auth status"],
    "pr create": [
        "# Title/body from the branch's Jira ticket, linked and transitioned",
        "bj pr create",
        "",
        "# From the last commit, into a specific base branch",
        "bj pr create --fill --base main",
        "",
        "# Preview without creating anything",
        "bj pr create --dry-run",
    ],
    "pr list": [
        "bj pr list",
        "bj pr list --state merged --limit 50",
        "bj pr list --json | jq '.[].title'",
    ],
    "pr view": [
        "# The PR for the current branch",
        "bj pr view",
        "bj pr view 42 --comments",
        "bj pr view --web",
    ],
    "pr merge": [
        "bj pr merge --squash --delete-branch",
        "bj pr merge 42 --dry-run",
    ],
    "issue list": [
        "bj issue list --jql \"project = PROJ AND status = 'In Progress'\"",
        "bj issue list --assignee me --status 'To Do'",
    ],
    "issue view": [
        "# Key from the current branch",
        "bj issue view",
        "bj issue view PROJ-42 --comments",
    ],
    "issue create": [
        'bj issue create --project PROJ --type Bug --summary "Login is broken"',
    ],
    "issue transition": [
        "# List available transitions",
        "bj issue transition PROJ-42",
        "# Perform one",
        'bj issue transition PROJ-42 "In Review"',
    ],
    "skill install": [
        "# Install for Claude Code in the current repo",
        "bj skill install --agent claude-code",
        "",
        "# Install for all agents at user scope",
        "bj skill install --scope user",
        "",
        "# Print the SKILL.md instead of installing",
        "bj skill install --print",
    ],
    "repo clone": ["bj repo clone myteam/myrepo"],
    "release list": [
        "bj release list --project PROJ",
        "bj release create 1.2.0 --project PROJ --release-date 2026-01-31",
        "bj release release 10000",
    ],
    "variable set": [
        "bj variable set DEPLOY_ENV production",
        "bj variable set API_TOKEN s3cret --secured",
    ],
    "config set": [
        "bj config get git_protocol",
        "bj config set bitbucket.workspace myteam",
    ],
    "search repos": [
        "bj search repos api --workspace myteam",
        'bj search code "TODO" --workspace myteam',
        "bj search issues \"project = PROJ AND status = 'In Progress'\"",
    ],
    "alias set": [
        "bj alias set prs 'pr list --state open'",
        "bj alias list",
    ],
    "pipeline run": [
        "bj pipeline run",
        "bj pipeline run --branch main --pipeline deploy",
    ],
    "pipeline logs": [
        "bj pipeline logs 123",
        "bj pipeline logs 123 --step 2",
    ],
    "browse": [
        "bj browse",
        "bj browse pr",
        "bj browse issue --no-browser",
    ],
    "api": [
        "bj api /repositories/{workspace}/{repo_slug}/pullrequests",
        "bj api --backend jira /myself",
        "bj api --backend jira -X POST /issue/PROJ-42/comment -f body=hi",
    ],
}


def _is_group(cmd: Any) -> bool:
    return bool(getattr(cmd, "commands", None))


def _one_liner(cmd: Any) -> str:
    text = (cmd.help or getattr(cmd, "short_help", "") or "").strip()
    return text.split("\n")[0]


def _metavar(param: Any) -> str:
    if param.param_type_name == "option" and getattr(param, "is_flag", False):
        return ""
    choices = getattr(param.type, "choices", None)
    if choices:
        return "{" + "|".join(choices) + "}"
    name = getattr(param.type, "name", "text") or "text"
    return f"<{name.lower()}>"


def _option_name(opt: Any) -> str:
    shorts = [o for o in opt.opts if len(o) == SHORT_OPT_LEN and o.startswith("-")]
    longs = [o for o in opt.opts if o not in shorts]
    return f"{', '.join(shorts + longs)} {_metavar(opt)}".strip()


def _default_note(opt: Any) -> str:
    if opt.required:
        return " _(required)_"
    if opt.default in (None, False, "", [], ()):
        return ""
    return f" _(default: {opt.default})_"


def _split_params(cmd: Any) -> tuple[list[Any], list[Any]]:
    args = [p for p in cmd.params if p.param_type_name == "argument"]
    opts = [p for p in cmd.params if p.param_type_name == "option"]
    return args, opts


def _synopsis(path: list[str], cmd: Any, *, is_group: bool) -> str:
    prefix = " ".join(["bj", *path]).strip()
    if is_group:
        return f"{prefix} <command> [OPTIONS]"
    args, _ = _split_params(cmd)
    parts = [prefix, "[OPTIONS]"]
    for arg in args:
        token = arg.name.upper()
        parts.append(token if arg.required else f"[{token}]")
    return " ".join(parts)


def _render_arguments(args: list[Any]) -> str:
    if not args:
        return ""
    lines = ["## Arguments", "", "| Argument | Description |", "| --- | --- |"]
    for arg in args:
        help_text = (getattr(arg, "help", None) or "").replace("\n", " ")
        required = " _(required)_" if arg.required else ""
        lines.append(f"| `{arg.name.upper()}` | {help_text}{required} |")
    return "\n".join(lines) + "\n"


def _render_options(opts: list[Any]) -> str:
    if not opts:
        return ""
    lines = ["## Options", "", "| Option | Description |", "| --- | --- |"]
    for opt in opts:
        help_text = (opt.help or "").replace("\n", " ")
        lines.append(f"| `{_option_name(opt)}` | {help_text}{_default_note(opt)} |")
    return "\n".join(lines) + "\n"


def _render_examples(key: str) -> str:
    if key not in EXAMPLES:
        return ""
    block = "\n".join(EXAMPLES[key])
    return f"## Examples\n\n```bash\n{block}\n```\n"


def _page(path: list[str], cmd: Any, *, is_group: bool,
          children: list[tuple[str, str]] | None = None) -> str:
    key = " ".join(path)
    label = " ".join(["bj", *path]).strip() or "bj"
    out = [
        "---",
        f"title: {label}",
        f"sidebar_label: {path[-1] if path else 'bj'}",
        "---",
        "",
        f"# {label}",
        "",
        _one_liner(cmd),
        "",
        "## Synopsis",
        "",
        "```",
        _synopsis(path, cmd, is_group=is_group),
        "```",
        "",
    ]
    if key in DESCRIPTIONS:
        out += ["## Description", "", DESCRIPTIONS[key], ""]
    if is_group and children:
        out += ["## Commands", "", "| Command | Description |", "| --- | --- |"]
        out += [f"| [`{name}`]({name}.md) | {desc} |" for name, desc in children]
        out.append("")
    else:
        args, opts = _split_params(cmd)
        for section in (_render_arguments(args), _render_options(opts), _render_examples(key)):
            if section:
                out.append(section)
    if path:
        parent_label = " ".join(["bj", *path[:-1]]).strip() or "bj"
        # Group index sits one level below root (../index.md); every leaf sits in
        # the same directory as its parent's index page (index.md).
        target = "../index.md" if is_group else "index.md"
        out += ["## See also", "", f"- [`{parent_label}`]({target})", ""]
    return "\n".join(out)


def _render_root(root: Any) -> str:
    out = [
        "---",
        "title: bj",
        "sidebar_label: Overview",
        "sidebar_position: 0",  # lead the Command reference section, not trail it
        "---",
        "",
        "# bj",
        "",
        "A gh-style CLI for Bitbucket (PRs, repos, pipelines) and Jira (issues).",
        "",
        "## Synopsis",
        "",
        "```",
        "bj <command> [OPTIONS]",
        "```",
        "",
        "## Description",
        "",
        DESCRIPTIONS[""],
        "",
    ]
    for heading, names in GROUPS:
        out += [f"## {heading}", "", "| Command | Description |", "| --- | --- |"]
        for name in names:
            sub = root.commands[name]
            link = f"{name}/index.md" if _is_group(sub) else f"{name}.md"
            out.append(f"| [`bj {name}`]({link}) | {_one_liner(sub)} |")
        out.append("")
    _, opts = _split_params(root)
    out.append(_render_options(opts))
    return "\n".join(out)


def _category(label: str, position: int, index_id: str) -> str:
    return json.dumps(
        {"label": label, "position": position,
         "link": {"type": "doc", "id": index_id}},
        indent=2,
    )


def _write(rel_path: str, content: str) -> None:
    dest = OUT_DIR / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    root = typer.main.get_command(app)
    (OUT_DIR / "_category_.json").write_text(
        _category("Command reference", 5, "reference/index"), encoding="utf-8"
    )
    _write("index.md", _render_root(root))

    group_pos = 0
    for name in [n for _, names in GROUPS for n in names]:
        cmd = root.commands[name]
        if _is_group(cmd):
            group_pos += 1
            children = [(sn, _one_liner(sc)) for sn, sc in cmd.commands.items()]
            _write(f"{name}/index.md", _page([name], cmd, is_group=True, children=children))
            (OUT_DIR / name / "_category_.json").write_text(
                _category(f"bj {name}", group_pos, f"reference/{name}/index"),
                encoding="utf-8",
            )
            for sn, sc in cmd.commands.items():
                _write(f"{name}/{sn}.md", _page([name, sn], sc, is_group=False))
        else:
            _write(f"{name}.md", _page([name], cmd, is_group=False))

    count = sum(1 for _ in OUT_DIR.rglob("*.md"))
    typer.echo(f"Generated {count} reference pages under {OUT_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
