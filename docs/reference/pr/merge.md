---
title: bj pr merge
sidebar_label: merge
---

# bj pr merge

Merge a pull request; transition the linked Jira ticket to done.

## Synopsis

```
bj pr merge [OPTIONS] [PR_ID]
```

## Description

Merge a pull request. If the PR's branch carries a Jira key, the linked ticket is transitioned to the configured done state on success.

## Arguments

| Argument | Description |
| --- | --- |
| `PR_ID` | PR id (default: current branch). |

## Options

| Option | Description |
| --- | --- |
| `-s, --squash` | Squash merge. |
| `--fast-forward` | Fast-forward merge. |
| `-d, --delete-branch` | Close source branch. |
| `-m, --message <text>` | Merge commit message. |
| `--no-jira` | Skip Jira transition. |
| `--dry-run` | Print actions; write nothing. |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj pr merge --squash --delete-branch
bj pr merge 42 --dry-run
```

## See also

- [`bj pr`](index.md)
