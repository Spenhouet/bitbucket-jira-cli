---
title: bj webhook view
---

# bj webhook view

View a single webhook.

## Synopsis

```
bj webhook view [OPTIONS] UID
```

## Arguments

| Argument | Description |
| --- | --- |
| `UID` | Webhook uuid (from `webhook list`). _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-R, --repo <text>` | WORKSPACE/REPO. |
| `-W, --workspace <text>` | Operate on a workspace's webhooks instead. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj webhook`](index.md)
