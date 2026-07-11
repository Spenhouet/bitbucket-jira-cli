---
sidebar_position: 3
title: Usage
---

# Usage

Install, authenticate, ship. The full flow:

```bash
# 1. Authenticate against Bitbucket and Jira (stores tokens in your keyring)
bj auth login

# 2. On a branch like feature/PROJ-42-thing, open a PR linked to PROJ-42
bj pr create

# 3. Review the ticket and the PR
bj issue view          # key read from the branch
bj pr view             # PR for the current branch

# 4. Merge (the linked ticket transitions to Done)
bj pr merge --squash --delete-branch
```

Other everyday commands:

```bash
bj repo view                 # inspect the current Bitbucket repository
bj pr list --state merged    # list pull requests
bj issue list --assignee me  # search Jira with shorthand filters (or --jql)
bj pipeline list             # Bitbucket Pipelines runs
bj browse pr                 # open the current PR in the browser
```

Every command, flag, and example is documented in the
[command reference](./reference/index.md). For scripting, see
[formatting output](./guides/formatting.md).
