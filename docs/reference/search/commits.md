---
title: bj search commits
---

# bj search commits

Search commit messages in one repository.

## Synopsis

```
bj search commits [OPTIONS] [QUERY]
```

## Arguments

| Argument | Description |
| --- | --- |
| `QUERY` | Text to match in the commit message. |

## Options

| Option | Description |
| --- | --- |
| `-R, --repo <text>` | WORKSPACE/REPO or REPO (default: current repo). |
| `-W, --workspace <text>` | Workspace (default: configured). |
| `--author <text>` | Filter by author (@me, name, email or account ID). |
| `-b, --branch <text>` | Branch or ref to search. |
| `--since <datetime>` | Stop at commits older than this date. |
| `-L, --limit <integer>` | Max results. _(default: 30)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj search commits "fix cache" --repo myteam/api
bj search commits --author @me --since 2026-01-01
```

## See also

- [`bj search`](index.md)
