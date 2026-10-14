---
title: bj pr task edit
---

# bj pr task edit

Edit a task's text.

## Synopsis

```
bj pr task edit [OPTIONS] TASK_ID
```

## Arguments

| Argument | Description |
| --- | --- |
| `TASK_ID` | Task id. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-b, --body <text>` | New text. |
| `-e, --editor` | Write in $EDITOR. |
| `--pr <integer>` | PR id (default: current branch). |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |

## See also

- [`bj pr task`](index.md)
