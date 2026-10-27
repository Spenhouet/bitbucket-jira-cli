---
title: bj board view
---

# bj board view

Show a board as columns of issues, like the Jira board view.

## Synopsis

```
bj board view [OPTIONS] [BOARD_ID]
```

## Arguments

| Argument | Description |
| --- | --- |
| `BOARD_ID` | Board id (from `board list`). Defaults to jira.board in the config, else the board of the current branch's project. |

## Options

| Option | Description |
| --- | --- |
| `--sprint <integer>` | Sprint id (from `board sprints`). Boards with sprints default to the active one. |
| `--mine` | Only show issues assigned to you. |
| `--jql <text>` | Only show issues matching this JQL filter. |
| `--done-days <integer>` | Hide issues done more than this many days ago. Team-managed boards default to 14 like Jira. 0 shows all. |
| `-L, --limit <integer>` | Maximum issues to load. _(default: 200)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj board`](index.md)
