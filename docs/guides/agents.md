---
title: Coding agents
description: Use bj with AI coding agents like Claude Code, Copilot, Cursor, Codex, and Gemini CLI. Install the bundled agent skill with bj skill install.
---

# Coding agents

`bj` is built for the terminal, so AI coding agents drive it the same way they
drive `gh`: one command, structured output, real exit codes, no interactive
detours. Because `bj` mirrors the GitHub CLI, an agent that already knows `gh`
needs almost no new instructions.

## Install the agent skill

`bj` ships an [Agent Skill](https://agentskills.io/): a `SKILL.md` playbook that
tells an agent how to drive `bj` (the `gh` mapping, the differences, the
non-interactive flags). Install it with one command, the way `gh skill install`
distributes skills, except the skill is bundled with the package you already
have, so there is no repository to fetch.

```bash
# Claude Code, current repository
bj skill install --agent claude-code

# All agents, available everywhere (home directory)
bj skill install --scope user
```

The flags mirror `gh skill install`:

- `--agent` picks the target. `claude-code` writes to `.claude/skills`,
  `github-copilot` to `.github/skills`, and any other agent shares
  `.agents/skills`.
- `--scope project` (default) installs into the current git repository;
  `--scope user` installs into your home directory.
- `--dir` overrides both with a path you choose.
- `--force` overwrites an existing copy; `--print` writes the `SKILL.md` to
  stdout instead of installing.

Source-tracking metadata is written into the installed skill's frontmatter, so
you can tell where it came from and which version.

### Other installers

The skill also lives in the repository under `skills/bitbucket-jira-cli/`, so the
cross-agent tools work too:

```bash
gh skill install Spenhouet/bitbucket-jira-cli
npx skills add Spenhouet/bitbucket-jira-cli
```

The `SKILL.md` format is the open [Agent Skills](https://agentskills.io/)
standard, shared by Claude Code, Copilot, Cursor, Codex, Gemini CLI, and others.

### Install as a Claude Code plugin

The skill is also published as an installable Claude Code plugin, so you can add
it without copying files. The repository doubles as a plugin marketplace:

```bash
/plugin marketplace add Spenhouet/bitbucket-jira-cli
/plugin install bitbucket-jira-cli@spenhouet
```

The first command registers the marketplace; the second installs the bundled
skill and keeps it managed by Claude Code, so updates arrive through `/plugin`
rather than a re-copy. Use this when you want Claude Code to own the skill's
lifecycle; use `bj skill install` when you want a plain copy in a specific
repository or agent directory.

## Always-on rules

A skill loads only when relevant. To keep `bj` in an agent's context all the
time, add a line to the project's `AGENTS.md` (or `CLAUDE.md`):

```markdown
## Bitbucket and Jira

Use `bj` for Bitbucket pull requests, repos, and pipelines, and Jira issues.
It mirrors `gh` (`gh pr` -> `bj pr`, `gh issue` -> `bj issue`). Authenticate
with `bj auth login`. Run `bj <command> --help` for flags.
```

## Running non-interactively

`bj` detects a non-TTY and skips prompts on its own. To be explicit in an agent
or CI environment:

- `BJ_PROMPT_DISABLED=1` never blocks on a prompt; pass inputs as flags or the
  command fails fast with a clear error.
- `NO_COLOR=1` drops color and the spinner.
- `--json` emits the full API payload; `--jq '<expr>'` filters it.
- `--yes` accepts confirmations; `--dry-run` (on `pr create`/`pr merge`)
  previews a write without making it.
- Exit codes are `0` success, `1` failure, `2` usage. See
  [Exit codes](./exit-codes.md).

Authenticate once with `bj auth login`. For headless runs, set
`BJ_BITBUCKET_TOKEN` and `BJ_JIRA_TOKEN` instead (see
[Environment](./environment.md)).
