---
title: bj search repos
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
| `-W, --workspace <text>` | Workspace (default: configured). |
| `-L, --limit <integer>` | Max results. _(default: 30)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj search repos api --workspace myteam
bj search code "TODO" --workspace myteam --language python
bj search code "TODO" --repo myteam/api --filename "src/*"
bj search issues "project = PROJ AND status = 'In Progress'"
bj search issues --assignee @me --state open --label backend
bj search issues -p PROJ --web
```

## See also

- [`bj search`](index.md)
