---
title: bj browse
sidebar_label: browse
---

# bj browse

Open the repository, current PR, or branch's Jira issue in the browser.

## Synopsis

```
bj browse [OPTIONS] [TARGET]
```

## Description

Open the repository, the current branch's pull request, or the branch's Jira issue in your browser. Use `--no-browser` to print the URL instead.

## Arguments

| Argument | Description |
| --- | --- |
| `TARGET` | 'pr', 'issue', or omit for the repo home. |

## Options

| Option | Description |
| --- | --- |
| `-n, --no-browser` | Print the URL only. |
| `-R, --repo <text>` | WORKSPACE/REPO. |

## Examples

```bash
bj browse
bj browse pr
bj browse issue --no-browser
```

## See also

- [`bj`](index.md)
