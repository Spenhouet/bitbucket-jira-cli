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
| `BJ_EDITOR`, `VISUAL`, `EDITOR` | Editor opened by `--editor` (and the `-e` body flags), in that precedence. |
| `BJ_PAGER`, `PAGER` | Pager for long output (`pr diff`, `pipeline logs`). Set to `cat` or empty to disable paging. |
| `BJ_PROMPT_DISABLED` | Set to any value to disable interactive prompts; commands then require their inputs as flags or error with "must provide --… when not running interactively". |
| `NO_COLOR` | Set to any value to disable ANSI colors and the progress spinner. |

## Interactive vs non-interactive

In a terminal, `bj` prompts for missing input (title, body, merge method),
shows a spinner during network calls, and asks before destructive actions like
`pr merge`, `pr close`, `pipeline stop` and `issue close`. Pass `--yes`/`-y` to
skip a confirmation. When output is piped, `BJ_PROMPT_DISABLED` is set, or stdin
is not a TTY, prompts and confirmations are skipped — supply everything via
flags (use `--json` for machine-readable output).

Token resolution order is env → OS keyring → `credentials.yml`; see
[Configuration](./configuration.md). Because the two backends use separate
credentials, you can supply one via the environment and the other via the
keyring independently — for example, exporting `BJ_BITBUCKET_TOKEN` in CI while
Jira stays logged out.
