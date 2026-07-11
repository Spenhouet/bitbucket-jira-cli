---
sidebar_position: 3
title: Usage
---

# Usage

:::note Bootstrap scaffold
The command tree below is the intended surface. Commands are wired to the
Bitbucket and Jira APIs as features land.
:::

```bash
bj auth login          # authenticate against Bitbucket and Jira
bj repo view           # inspect the current Bitbucket repository
bj pr create           # open a PR; auto-fill from the branch's Jira key
bj pr view             # show the PR for the current branch
bj issue view PROJ-42  # show a Jira issue
bj pipeline list       # list Bitbucket Pipelines runs
```

See [`bj --help`](/) for the live command list.
