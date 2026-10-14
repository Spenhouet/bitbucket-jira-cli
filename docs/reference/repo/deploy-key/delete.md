---
title: bj repo deploy-key delete
---

# bj repo deploy-key delete

Delete a repository access key.

## Synopsis

```
bj repo deploy-key delete [OPTIONS] KEY_ID
```

## Arguments

| Argument | Description |
| --- | --- |
| `KEY_ID` | Key id (from `deploy-key list`). _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-R, --repo <text>` | WORKSPACE/REPO (default: git remote). |
| `-y, --yes` | Skip the confirmation prompt. |

## See also

- [`bj repo deploy-key`](index.md)
