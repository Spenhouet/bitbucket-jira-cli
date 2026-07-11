---
title: bj
sidebar_label: Overview
sidebar_position: 0
---

# bj

A gh-style CLI for Bitbucket (PRs, repos, pipelines) and Jira (issues).

## Synopsis

```
bj <command> [OPTIONS]
```

## Description

`bj` brings the ergonomics of GitHub's `gh` CLI to Bitbucket Cloud and Jira Cloud. It manages Bitbucket pull requests, repositories and pipelines and Jira issues from a single noun-first command surface, and reads the Jira key from your git branch to auto-link and transition tickets. See the [branch-key workflow](../guides/branch-key.md) guide.

## Core commands

| Command | Description |
| --- | --- |
| [`bj auth`](auth/index.md) | Authenticate bj with Bitbucket and Jira. |
| [`bj repo`](repo/index.md) | Work with Bitbucket repositories. |
| [`bj pr`](pr/index.md) | Manage Bitbucket pull requests. |
| [`bj issue`](issue/index.md) | Manage Jira issues. |

## Pipelines

| Command | Description |
| --- | --- |
| [`bj pipeline`](pipeline/index.md) | Work with Bitbucket Pipelines. |

## Utility

| Command | Description |
| --- | --- |
| [`bj browse`](browse.md) | Open the repository, current PR, or branch's Jira issue in the browser. |
| [`bj api`](api.md) | Make an authenticated request to the Bitbucket or Jira API. |

## Options

| Option | Description |
| --- | --- |
| `--version` | Show the version and exit. |
| `--install-completion` | Install completion for the current shell. |
| `--show-completion` | Show completion for the current shell, to copy it or customize the installation. |
