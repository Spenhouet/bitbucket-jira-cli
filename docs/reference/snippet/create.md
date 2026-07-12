---
title: bj snippet create
sidebar_label: create
---

# bj snippet create

Create a snippet from files or stdin (like `gh gist create`).

## Synopsis

```
bj snippet create [OPTIONS] FILES
```

## Arguments

| Argument | Description |
| --- | --- |
| `FILES` | File paths, or - to read stdin. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-t, --title <text>` | Snippet title. |
| `--public` | Make it public (default private). |
| `-f, --filename <text>` | Filename to use for stdin content. |
| `-w, --workspace <text>` | Workspace (default: configured). |
| `-w, --web` | Open the snippet after creating. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj snippet`](index.md)
