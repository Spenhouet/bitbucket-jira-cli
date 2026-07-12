---
title: bj search repos
sidebar_label: repos
---

# bj search repos

Search repositories in a workspace by name.

## Synopsis

```
bj search repos [OPTIONS] QUERY
```

## Arguments

| Argument | Description |
| --- | --- |
| `QUERY` | Text to match in repository names. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-w, --workspace <text>` | Workspace (default: configured). |
| `-L, --limit <integer>` | Max results. _(default: 30)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj search repos api --workspace myteam
bj search code "TODO" --workspace myteam
bj search issues "project = PROJ AND status = 'In Progress'"
```

## See also

- [`bj search`](index.md)
