---
title: bj repo create
sidebar_label: create
---

# bj repo create

Create a new repository (needs a token with repository write scope).

## Synopsis

```
bj repo create [OPTIONS] REPO
```

## Arguments

| Argument | Description |
| --- | --- |
| `REPO` | WORKSPACE/REPO (or REPO with a default workspace). _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-d, --description <text>` |  |
| `--private` | Repository visibility. _(default: True)_ |
| `--project <text>` | Project key to create the repo under. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj repo`](index.md)
