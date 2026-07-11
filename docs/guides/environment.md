---
sidebar_position: 4
title: Environment variables
---

# Environment variables

`bj` reads the following environment variables.

| Variable | Purpose |
| --- | --- |
| `BJ_BITBUCKET_TOKEN` | Bitbucket API token. Takes precedence over the keyring and is never written to disk. |
| `BJ_JIRA_TOKEN` | Jira API token. Same precedence and handling as above. |
| `BJ_CONFIG_DIR` | Override the config directory (default: `$XDG_CONFIG_HOME/bitbucket-jira-cli`). |
| `XDG_CONFIG_HOME` | Base directory for config when `BJ_CONFIG_DIR` is unset (default: `~/.config`). |
| `BROWSER` | The web browser [`bj browse`](../reference/browse.md) (and `--web` flags) open URLs with. |
| `NO_COLOR` | Set to any value to disable ANSI colors in rendered output. |

Token resolution order is env → OS keyring → `credentials.yml`; see
[Configuration](./configuration.md). Because the two backends use separate
credentials, you can supply one via the environment and the other via the
keyring independently — for example, exporting `BJ_BITBUCKET_TOKEN` in CI while
Jira stays logged out.
