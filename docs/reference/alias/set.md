---
title: bj alias set
---

# bj alias set

Create or update an alias.

## Synopsis

```
bj alias set [OPTIONS] NAME EXPANSION
```

## Arguments

| Argument | Description |
| --- | --- |
| `NAME` | Alias name. _(required)_ |
| `EXPANSION` | Command it expands to, e.g. 'pr list'. _(required)_ |

## Examples

```bash
bj alias set prs 'pr list --state open'
bj alias list
```

## See also

- [`bj alias`](index.md)
