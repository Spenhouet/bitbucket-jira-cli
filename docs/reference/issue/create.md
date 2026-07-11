---
title: bj issue create
sidebar_label: create
---

# bj issue create

Create a Jira issue.

## Synopsis

```
bj issue create [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `-p, --project <text>` | Project key. |
| `-t, --type <text>` | Issue type. _(default: Task)_ |
| `-s, --summary <text>` | Summary/title. |
| `-b, --body <text>` | Description. |
| `-e, --editor` | Write the body in $EDITOR. |
| `-a, --assignee <text>` | Assignee (name/email, or 'me'). |
| `-l, --label <text>` | Label. |
| `--priority <text>` | Priority name. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj issue create --project PROJ --type Bug --summary "Login is broken"
```

## See also

- [`bj issue`](index.md)
