---
title: bj webhook edit
---

# bj webhook edit

Edit a webhook. Only the fields you pass change.

## Synopsis

```
bj webhook edit [OPTIONS] UID
```

## Arguments

| Argument | Description |
| --- | --- |
| `UID` | Webhook uuid. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-u, --url <text>` | New payload URL. |
| `-e, --event <text>` | Replace the event list; repeat for several. |
| `-d, --description <text>` | New label. |
| `--secret <text>` | Replace the secret. |
| `--active` | Enable or disable the webhook. |
| `-R, --repo <text>` | WORKSPACE/REPO. |
| `-W, --workspace <text>` | Operate on a workspace's webhooks instead. |

## See also

- [`bj webhook`](index.md)
