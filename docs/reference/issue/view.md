---
title: bj issue view
---

# bj issue view

View a Jira issue.

## Synopsis

```
bj issue view [OPTIONS] [KEY]
```

## Description

View a Jira issue. With no key, the key is read from the current git branch name.

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Issue key (default: from branch). |

## Options

| Option | Description |
| --- | --- |
| `-c, --comments` | Show comments. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
# Key from the current branch
bj issue view
bj issue view PROJ-42 --comments
```

## See also

- [`bj issue`](index.md)
