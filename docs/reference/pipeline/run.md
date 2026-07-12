---
title: bj pipeline run
---

# bj pipeline run

Trigger a pipeline run.

## Synopsis

```
bj pipeline run [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `--branch <text>` | Ref to run on (default: current). |
| `--pipeline <text>` | Custom pipeline name to run. |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj pipeline run
bj pipeline run --branch main --pipeline deploy
```

## See also

- [`bj pipeline`](index.md)
