---
title: bj repo edit
---

# bj repo edit

Edit repository settings (description, visibility, name).

## Synopsis

```
bj repo edit [OPTIONS] [REPO]
```

## Arguments

| Argument | Description |
| --- | --- |
| `REPO` | WORKSPACE/REPO (default: git remote). |

## Options

| Option | Description |
| --- | --- |
| `-d, --description <text>` |  |
| `--private` | Change visibility. |
| `--name <text>` | Rename the repository. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj repo`](index.md)
