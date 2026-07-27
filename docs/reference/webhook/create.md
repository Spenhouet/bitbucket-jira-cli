---
title: bj webhook create
---

# bj webhook create

Create a webhook. See `bj webhook events` for the event names.

## Synopsis

```
bj webhook create [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `-u, --url <text>` | Payload URL to POST events to. _(required)_ |
| `-e, --event <text>` | Event to subscribe to; repeat for several. |
| `-d, --description <text>` | Label (default: the URL). |
| `--secret <text>` | Shared secret used to sign payloads. |
| `--inactive` | Create it disabled. |
| `-R, --repo <text>` | WORKSPACE/REPO. |
| `-W, --workspace <text>` | Operate on a workspace's webhooks instead. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
# Subscribe the current repo to pushes and PR events
bj webhook create --url https://example.com/hook -e repo:push -e pullrequest:created

# Workspace-level, signed, with a label
bj webhook create -W myteam -u https://example.com/hook -e repo:push \
  --secret "$HOOK_SECRET" -d "CI trigger"
```

## See also

- [`bj webhook`](index.md)
