---
title: bj automation
---

# bj automation

Manage Jira automation rules (needs an unscoped Jira token).

## Synopsis

```
bj automation <command> [OPTIONS]
```

## Description

Jira automation rules. They live behind the Jira Automation REST API (`api.atlassian.com/automation/public/jira/{cloudId}/rest/v1`), not the platform API, and `bj` resolves the cloudId from the site for you. The rule endpoints need a Jira administrator, and Atlassian documents only **unscoped** API tokens for this API: a scoped token gets `401 scope does not match`. If your login uses a scoped token, set `BJ_JIRA_TOKEN` to an unscoped one for these commands. `export` and `import` copy a rule: `import` drops the source rule's UUID, timestamps and component ids and creates the rule disabled unless you pass `--enable`.

## Commands

| Command | Description |
| --- | --- |
| [`list`](list.md) | List automation rules (name, UUID, state, scope). |
| [`view`](view.md) | View one rule; --json prints its full definition. |
| [`enable`](enable.md) | Enable a rule. |
| [`disable`](disable.md) | Disable a rule. |
| [`export`](export.md) | Export a rule definition as JSON, ready for `bj automation import`. |
| [`import`](import.md) | Create a rule from an exported definition. |
| [`delete`](delete.md) | Delete a rule. Jira only deletes disabled rules. |

## See also

- [`bj`](../index.md)
