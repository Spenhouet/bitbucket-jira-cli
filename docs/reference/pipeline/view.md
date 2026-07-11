---
title: bj pipeline view
sidebar_label: view
---

# bj pipeline view

View a pipeline run and its steps.

## Synopsis

```
bj pipeline view [OPTIONS] PIPELINE
```

## Arguments

| Argument | Description |
| --- | --- |
| `PIPELINE` | Build number or pipeline UUID. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj pipeline`](index.md)
