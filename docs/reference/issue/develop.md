---
title: bj issue develop
sidebar_label: develop
---

# bj issue develop

Create a local git branch for an issue (its key drives branch-key automation).

## Synopsis

```
bj issue develop [OPTIONS] [KEY]
```

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Issue key (default: from branch). |

## Options

| Option | Description |
| --- | --- |
| `--base <text>` | Base ref to branch from. |
| `--name <text>` | Override the branch name. |
| `--checkout` | Check out the new branch. _(default: True)_ |

## See also

- [`bj issue`](index.md)
