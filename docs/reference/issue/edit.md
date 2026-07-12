---
title: bj issue edit
---

# bj issue edit

Edit a Jira issue: summary, description, assignee, labels, priority, or any --field.

## Synopsis

```
bj issue edit [OPTIONS] [KEY]
```

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Issue key (default: from branch). |

## Options

| Option | Description |
| --- | --- |
| `-s, --summary <text>` | New summary. |
| `-b, --body <text>` | New description. |
| `-e, --editor` | Write the body in $EDITOR. |
| `-a, --assignee <text>` | Assignee (name/email, or 'me'). |
| `-l, --label <text>` | Label; prefix '-' to remove. |
| `--priority <text>` | Priority name. |
| `--field <text>` | Set any field: 'Name=Value' (repeatable). |

## See also

- [`bj issue`](index.md)
