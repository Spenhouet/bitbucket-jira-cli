---
title: bj issue list
sidebar_label: list
---

# bj issue list

Search Jira issues with JQL or shorthand filters.

## Synopsis

```
bj issue list [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `--jql <text>` | Raw JQL query. |
| `-s, --status <text>` | Filter by status. |
| `-a, --assignee <text>` | Filter by assignee (accountId or 'me'). |
| `-t, --type <text>` | Filter by issue type. |
| `-p, --project <text>` | Filter by project key. |
| `-l, --label <text>` | Filter by label. |
| `-L, --limit <integer>` | Max results. _(default: 30)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj issue list --jql "project = PROJ AND status = 'In Progress'"
bj issue list --assignee me --status 'To Do'
```

## See also

- [`bj issue`](index.md)
