---
title: bj repo list
---

# bj repo list

List repositories in a workspace.

## Synopsis

```
bj repo list [OPTIONS] [WORKSPACE]
```

## Arguments

| Argument | Description |
| --- | --- |
| `WORKSPACE` | Workspace (default: configured). |

## Options

| Option | Description |
| --- | --- |
| `--role <text>` | owner|admin|contributor|member. |
| `-L, --limit <integer>` | Max results. _(default: 30)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj repo`](index.md)
