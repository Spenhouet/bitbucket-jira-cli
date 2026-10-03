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

Search Bitbucket repositories, code, pull requests and commits, and Jira issues (JQL). Filter flags such as `--language` or `--assignee` are turned into Bitbucket search modifiers, BBQL or JQL for you. `search prs` covers the whole workspace in one request with `--author`; without it, every repository is queried. `search commits` works on one repository, since Bitbucket cannot filter commits on the server. Jira issue search is also available as `bj issue list --jql`.

## Commands

| Command | Description |
| --- | --- |
| [`repos`](repos.md) | Search repositories in a workspace by name. |
| [`code`](code.md) | Search code across a workspace. |
| [`prs`](prs.md) | Search pull requests across a workspace. |
| [`commits`](commits.md) | Search commit messages in one repository. |
| [`issues`](issues.md) | Search Jira issues with JQL and/or gh-style filter flags. |

## See also

- [`bj`](../index.md)
