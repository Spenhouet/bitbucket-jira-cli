---
title: bj issue create
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
| `--parent <text>` | Parent issue key (or id): the epic, or the parent of a sub-task. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj issue create --project PROJ --type Bug --summary "Login is broken"

# A sub-task needs its parent at creation time
bj issue create --project PROJ --type Subtask --parent PROJ-42 --summary "Add tests"

# A story under an epic
bj issue create --project PROJ --type Story --parent PROJ-10 --summary "Login page"
```

## See also

- [`bj issue`](index.md)
