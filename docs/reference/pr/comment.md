---
title: bj pr comment
sidebar_label: comment
---

# bj pr comment

Comment on a PR: top-level, inline (--file/--line), reply (--reply-to), or manage.

## Synopsis

```
bj pr comment [OPTIONS] [PR_ID]
```

## Arguments

| Argument | Description |
| --- | --- |
| `PR_ID` | PR id (default: current branch). |

## Options

| Option | Description |
| --- | --- |
| `-b, --body <text>` | Comment text. |
| `-e, --editor` | Write in $EDITOR. |
| `--file <text>` | Inline comment: file path. |
| `--line <integer>` | Inline comment: line number. |
| `--side <text>` | Inline side: new|old. _(default: new)_ |
| `--reply-to <integer>` | Reply to a comment id. |
| `--edit <integer>` | Edit a comment id. |
| `--delete <integer>` | Delete a comment id. |
| `--resolve <integer>` | Resolve a thread. |
| `--unresolve <integer>` | Unresolve a thread. |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |

## See also

- [`bj pr`](index.md)
