---
title: bj search
---

# bj search

Search Bitbucket and Jira.

## Synopsis

```
bj search <command> [OPTIONS]
```

## Description

Search Bitbucket repositories and code and Jira issues (JQL). Filter flags such as `--language` or `--assignee` are turned into Bitbucket search modifiers or JQL for you. Bitbucket has no workspace-wide search API for commits or pull requests, so there is no `search commits` or `search prs`; use `bj pr list` per repository. Jira issue search is also available as `bj issue list --jql`.

## Commands

| Command | Description |
| --- | --- |
| [`repos`](repos.md) | Search repositories in a workspace by name. |
| [`code`](code.md) | Search code across a workspace. |
| [`issues`](issues.md) | Search Jira issues with JQL and/or gh-style filter flags. |

## See also

- [`bj`](../index.md)
