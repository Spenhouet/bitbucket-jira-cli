---
title: bj repo fork
---

# bj repo fork

Fork a repository into a workspace.

## Synopsis

```
bj repo fork [OPTIONS] REPO
```

## Arguments

| Argument | Description |
| --- | --- |
| `REPO` | Source WORKSPACE/REPO to fork. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `--workspace <text>` | Destination workspace (default: yours). |
| `--name <text>` | Name for the fork. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj repo`](index.md)
