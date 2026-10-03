---
title: bj search code
---

# bj search code

Search code across a workspace.

## Synopsis

```
bj search code [OPTIONS] QUERY
```

## Arguments

| Argument | Description |
| --- | --- |
| `QUERY` | Code search query. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-W, --workspace <text>` | Workspace (default: configured). |
| `-R, --repo <text>` | Restrict to a repository (REPO or WORKSPACE/REPO). |
| `--language <text>` | Restrict to a language (lang:). |
| `--extension <text>` | Restrict to a file extension (ext:). |
| `--path, --filename <text>` | Restrict to a path or file name (path:). |
| `-L, --limit <integer>` | Max results. _(default: 30)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj search`](index.md)
