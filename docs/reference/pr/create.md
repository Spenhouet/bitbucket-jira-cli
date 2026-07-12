---
title: bj pr create
---

# bj pr create

Open a pull request; auto-link and transition the branch's Jira ticket.

## Synopsis

```
bj pr create [OPTIONS]
```

## Description

Open a pull request for the current branch. When the branch name carries a Jira key (e.g. `feature/PROJ-42-thing`), `bj` fills the title from the ticket, links the PR to the issue, and transitions the ticket to the configured in-progress state. Use `--no-jira` to skip that, or `--dry-run` to preview without writing. See [branch-key workflow](../../guides/branch-key.md).

## Options

| Option | Description |
| --- | --- |
| `-t, --title <text>` | PR title. |
| `-b, --body <text>` | PR description. |
| `-B, --base <text>` | Target branch. |
| `-H, --head <text>` | Source branch. |
| `-r, --reviewer <text>` | Reviewer account_id or {uuid}. |
| `-d, --draft` | Create as draft. |
| `-f, --fill` | Title/body from last commit. |
| `-e, --editor` | Write the body in $EDITOR. |
| `--no-jira` | Skip Jira link/transition. |
| `--dry-run` | Print actions; write nothing. |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
# Title/body from the branch's Jira ticket, linked and transitioned
bj pr create

# From the last commit, into a specific base branch
bj pr create --fill --base main

# Preview without creating anything
bj pr create --dry-run
```

## See also

- [`bj pr`](index.md)
