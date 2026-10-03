---
title: bj search prs
---

# bj search prs

Search pull requests across a workspace.

## Synopsis

```
bj search prs [OPTIONS] [QUERY]
```

## Arguments

| Argument | Description |
| --- | --- |
| `QUERY` | Text to match in the title or description. |

## Options

| Option | Description |
| --- | --- |
| `-W, --workspace <text>` | Workspace (default: configured). |
| `-R, --repo <text>` | Restrict to a repository (REPO or WORKSPACE/REPO). |
| `--author <text>` | Filter by author (@me, account ID or {UUID}). |
| `-s, --state {open|merged|declined|superseded|all}` | Filter by state. _(default: all)_ |
| `-B, --base <text>` | Filter by destination branch. |
| `-H, --head <text>` | Filter by source branch. |
| `-L, --limit <integer>` | Max results. _(default: 30)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
# Your merged PRs across the workspace (one request)
bj search prs cache --author @me --state merged

# Open PRs into main in every repository
bj search prs --state open --base main
```

## See also

- [`bj search`](index.md)
