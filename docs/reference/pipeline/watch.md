---
title: bj pipeline watch
sidebar_label: watch
---

# bj pipeline watch

Follow a running pipeline until it finishes.

## Synopsis

```
bj pipeline watch [OPTIONS] PIPELINE
```

## Arguments

| Argument | Description |
| --- | --- |
| `PIPELINE` | Build number or pipeline UUID. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `--interval <integer>` | Poll seconds. _(default: 5)_ |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |

## See also

- [`bj pipeline`](index.md)
