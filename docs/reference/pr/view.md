---
title: bj pr view
---

# bj pr view

View a pull request.

## Synopsis

```
bj pr view [OPTIONS] [PR_ID]
```

## Arguments

| Argument | Description |
| --- | --- |
| `PR_ID` | PR id (default: current branch). |

## Options

| Option | Description |
| --- | --- |
| `-c, --comments` | Show comments. |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |
| `-w, --web` | Open in the browser. |

## Examples

```bash
# The PR for the current branch
bj pr view
bj pr view 42 --comments
bj pr view --web
```

## See also

- [`bj pr`](index.md)
