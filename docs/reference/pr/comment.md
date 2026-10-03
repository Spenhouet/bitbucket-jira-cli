---
title: bj pr comment
---

# bj pr comment

Comment on a PR: top-level, inline (--file/--line), reply (--reply-to), or manage.

## Synopsis

```
bj pr comment [OPTIONS] [PR_ID]
```

## Description

Comment on a pull request. With `--pending` the comment is saved as a draft that only you can see. It is published together with your other pending comments when you press *Finish review* on the pull request in Bitbucket, since the Bitbucket Cloud API has no call that publishes them.

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
| `--pending` | Save as a pending review comment, visible only to you until you finish the review in Bitbucket. |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |

## Examples

```bash
bj pr comment 42 --body 'Looks good'
bj pr comment 42 --file src/app.py --line 12 --body 'Typo here'
# Draft review comments, published later from the web UI
bj pr comment 42 --file src/app.py --line 12 --body 'Nit' --pending
```

## See also

- [`bj pr`](index.md)
