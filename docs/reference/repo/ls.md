---
title: bj repo ls
---

# bj repo ls

List files in a repository directory.

## Synopsis

```
bj repo ls [OPTIONS] [PATH]
```

## Arguments

| Argument | Description |
| --- | --- |
| `PATH` | Directory path (default: root). |

## Options

| Option | Description |
| --- | --- |
| `--ref <text>` | Branch, tag, or commit. _(default: HEAD)_ |
| `-R, --repo <text>` | WORKSPACE/REPO (default: git remote). |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj repo`](index.md)
