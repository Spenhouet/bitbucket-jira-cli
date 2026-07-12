---
title: bj issue
---

# bj issue

Manage Jira issues.

## Synopsis

```
bj issue <command> [OPTIONS]
```

## Commands

| Command | Description |
| --- | --- |
| [`fields`](fields.md) | List the editable fields on an issue (name, id, type, value, allowed values). |
| [`list`](list.md) | Search Jira issues with JQL or shorthand filters. |
| [`view`](view.md) | View a Jira issue. |
| [`create`](create.md) | Create a Jira issue. |
| [`edit`](edit.md) | Edit a Jira issue: summary, description, assignee, labels, priority, or any --field. |
| [`comment`](comment.md) | Add a comment to a Jira issue. |
| [`transition`](transition.md) | Transition an issue, choosing from the available states when none is given. |
| [`close`](close.md) | Close a Jira issue (transition to the configured done state). |
| [`develop`](develop.md) | Create a local git branch for an issue (its key drives branch-key automation). |
| [`delete`](delete.md) | Delete a Jira issue (irreversible). |
| [`status`](status.md) | Show open Jira issues assigned to you. |

## See also

- [`bj`](../index.md)
