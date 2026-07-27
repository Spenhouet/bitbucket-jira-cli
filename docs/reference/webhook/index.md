---
title: bj webhook
---

# bj webhook

Manage Bitbucket webhooks.

## Synopsis

```
bj webhook <command> [OPTIONS]
```

## Description

Bitbucket webhooks. Bitbucket registers them on one of two subject types, a single repository or a whole workspace, so commands default to the current repository and `--workspace NAME` switches to workspace scope. Run `bj webhook events` for the event names you can subscribe to. There is no `forward` subcommand: the `gh webhook` extension's forwarding relies on a GitHub-side relay that Bitbucket has no equivalent for.

## Commands

| Command | Description |
| --- | --- |
| [`list`](list.md) | List webhooks on a repository or workspace. |
| [`view`](view.md) | View a single webhook. |
| [`create`](create.md) | Create a webhook. See `bj webhook events` for the event names. |
| [`edit`](edit.md) | Edit a webhook. Only the fields you pass change. |
| [`delete`](delete.md) | Delete a webhook. |
| [`events`](events.md) | List the events a webhook can subscribe to. |

## See also

- [`bj`](../index.md)
