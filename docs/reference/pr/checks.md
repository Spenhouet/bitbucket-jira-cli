---
title: bj pr checks
---

# bj pr checks

Show the build/commit statuses (CI checks) for a pull request.

## Synopsis

```
bj pr checks [OPTIONS] [PR_ID]
```

## Arguments

| Argument | Description |
| --- | --- |
| `PR_ID` | PR id (default: current branch). |

## Options

| Option | Description |
| --- | --- |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj pr`](index.md)
