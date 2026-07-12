---
title: bj board
sidebar_label: board
---

# bj board

Work with Jira boards and sprints.

## Synopsis

```
bj board <command> [OPTIONS]
```

## Description

Jira Software boards and sprints, the closest analog to GitHub Projects. This uses the Jira agile API. A scoped token needs the extra scopes `read:board-scope:jira-software`, `read:sprint:jira-software`, and `read:project:jira` (an unscoped token has them implicitly).

## Commands

| Command | Description |
| --- | --- |
| [`list`](list.md) | List Jira boards. |
| [`sprints`](sprints.md) | List a board's sprints. |

## See also

- [`bj`](../index.md)
