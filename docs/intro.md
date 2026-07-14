---
title: Introduction
---

# Bitbucket Jira CLI (`bj`)

`bj` is a command-line tool that brings [GitHub `gh`](https://cli.github.com/)
ergonomics to Bitbucket and Jira. It manages Bitbucket pull requests, repos and
pipelines and Jira issues from one noun-first command surface. It is
terminal-native and scriptable, which makes it a natural fit for AI coding
agents (see [Coding agents](./guides/agents.md)).

The signature feature is **branch-name-as-Jira-key**: your current git branch
carries a Jira key (e.g. `feature/PROJ-42-thing`), and commands use it to
auto-link pull requests to tickets and drive Jira transitions. See the
[branch-key workflow](./guides/branch-key.md) guide.

`bj` works with Bitbucket Cloud and Jira Cloud. Bitbucket and Jira Server or
Data Center are not supported yet. Contributions to add on-prem support are
welcome.

## Next steps

- [Installation](./installation.md): install with uv, pip, or Docker.
- [Usage](./usage.md): the three-step flow.
- [Guides](./guides/branch-key.md): branch keys, coding agents, configuration, output formatting.
- [Command reference](./reference/index.md): every command, generated from the CLI.
