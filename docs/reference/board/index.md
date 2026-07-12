---
title: bj board
sidebar_label: board
---

# bj board

Work with Jira boards and sprints (needs an unscoped Jira token).

## Synopsis

```
bj board <command> [OPTIONS]
```

## Description

Jira Software boards and sprints, the closest analog to GitHub Projects. This uses the Jira agile API, whose scopes Atlassian only grants to OAuth/Forge apps, so `bj board` works with an **unscoped** Jira token (`jira.auth_mode: site`), not a scoped/gateway one.

## Commands

| Command | Description |
| --- | --- |
| [`list`](list.md) | List Jira boards. |
| [`sprints`](sprints.md) | List a board's sprints. |

## See also

- [`bj`](../index.md)
