---
title: bj repo clone
sidebar_label: clone
---

# bj repo clone

Clone a repository locally (HTTPS uses your bj token automatically).

## Synopsis

```
bj repo clone [OPTIONS] REPO [DIRECTORY]
```

## Arguments

| Argument | Description |
| --- | --- |
| `REPO` | WORKSPACE/REPO to clone. _(required)_ |
| `DIRECTORY` | Target directory. |

## Options

| Option | Description |
| --- | --- |
| `--protocol <text>` | https or ssh (default: configured). |

## Examples

```bash
bj repo clone myteam/myrepo
```

## See also

- [`bj repo`](index.md)
