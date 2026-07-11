---
title: bj pr edit
sidebar_label: edit
---

# bj pr edit

Edit an open pull request's title, description, target branch or reviewers.

## Synopsis

```
bj pr edit [OPTIONS] [PR_ID]
```

## Arguments

| Argument | Description |
| --- | --- |
| `PR_ID` | PR id (default: current branch). |

## Options

| Option | Description |
| --- | --- |
| `-t, --title <text>` | New title. |
| `-b, --body <text>` | New description. |
| `-B, --base <text>` | New target branch. |
| `-r, --reviewer <text>` | Set reviewers (repeatable; replaces the set). |
| `-e, --editor` | Edit the body in $EDITOR. |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj pr`](index.md)
