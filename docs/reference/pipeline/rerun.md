---
title: bj pipeline rerun
sidebar_label: rerun
---

# bj pipeline rerun

Re-run a pipeline with the same target (Bitbucket has no native rerun).

## Synopsis

```
bj pipeline rerun [OPTIONS] PIPELINE
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
