---
title: bj pipeline logs
---

# bj pipeline logs

Print the logs for a pipeline's steps.

## Synopsis

```
bj pipeline logs [OPTIONS] PIPELINE
```

## Arguments

| Argument | Description |
| --- | --- |
| `PIPELINE` | Build number or pipeline UUID. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `--step <integer>` | 1-based step index (default: all). |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |

## Examples

```bash
bj pipeline logs 123
bj pipeline logs 123 --step 2
```

## See also

- [`bj pipeline`](index.md)
