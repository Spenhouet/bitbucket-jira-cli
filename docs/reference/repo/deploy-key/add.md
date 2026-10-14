---
title: bj repo deploy-key add
---

# bj repo deploy-key add

Add an access key to a repository.

## Synopsis

```
bj repo deploy-key add [OPTIONS] KEY_FILE
```

## Arguments

| Argument | Description |
| --- | --- |
| `KEY_FILE` | Path to the public key file. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-t, --title <text>` | Label for the key. _(required)_ |
| `-R, --repo <text>` | WORKSPACE/REPO (default: git remote). |

## See also

- [`bj repo deploy-key`](index.md)
