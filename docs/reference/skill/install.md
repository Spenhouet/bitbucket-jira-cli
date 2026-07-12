---
title: bj skill install
sidebar_label: install
---

# bj skill install

Install the bj agent skill so coding agents know how to drive `bj`.

## Synopsis

```
bj skill install [OPTIONS]
```

## Description

Copy the bundled agent skill into an agent's skills directory. The target follows the same conventions as `gh skill install`: `--scope project` (default) writes into the current repository, `--scope user` into your home directory, and `--agent` selects the directory (`claude-code` uses `.claude/skills`, others share `.agents/skills`). `--print` writes the `SKILL.md` to stdout instead.

## Options

| Option | Description |
| --- | --- |
| `-a, --agent <text>` | Target agent (e.g. claude-code, github-copilot). |
| `-s, --scope <text>` | Install location: 'project' or 'user'. _(default: project)_ |
| `-d, --dir <path>` | Custom directory (overrides --agent and --scope). |
| `-f, --force` | Overwrite an existing skill without asking. |
| `--print` | Write the SKILL.md to stdout instead of installing. |

## Examples

```bash
# Install for Claude Code in the current repo
bj skill install --agent claude-code

# Install for all agents at user scope
bj skill install --scope user

# Print the SKILL.md instead of installing
bj skill install --print
```

## See also

- [`bj skill`](index.md)
