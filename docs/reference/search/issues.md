---
title: bj search issues
---

# bj search issues

Search Jira issues with JQL and/or gh-style filter flags.

## Synopsis

```
bj search issues [OPTIONS] [JQL]
```

## Arguments

| Argument | Description |
| --- | --- |
| `JQL` | JQL query (optional with filters). |

## Options

| Option | Description |
| --- | --- |
| `--assignee <text>` | Filter by assignee (accountId or @me). |
| `--author <text>` | Filter by reporter (accountId or @me). |
| `-s, --state {open|closed}` | Filter by state (Jira status category). |
| `-p, --project <text>` | Filter by project key. |
| `-t, --type <text>` | Filter by issue type. |
| `-l, --label <text>` | Filter by label (repeatable). |
| `-w, --web` | Open the search in the browser. |
| `-L, --limit <integer>` | Max results. _(default: 30)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj search`](index.md)
