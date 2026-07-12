---
title: bj pr reopen
sidebar_label: reopen
---

# bj pr reopen

Reopen a declined pull request by opening a fresh one from the same branches.

## Synopsis

```
bj pr reopen [OPTIONS] PR_ID
```

## Arguments

| Argument | Description |
| --- | --- |
| `PR_ID` | Declined PR id to reopen. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj pr`](index.md)
