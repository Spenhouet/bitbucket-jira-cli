---
title: bj issue transition
sidebar_label: transition
---

# bj issue transition

Transition an issue, choosing from the available states when none is given.

## Synopsis

```
bj issue transition [OPTIONS] [KEY] [STATE]
```

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Issue key (default: from branch). |
| `STATE` | Target state (omit to choose interactively). |

## Examples

```bash
# List available transitions
bj issue transition PROJ-42
# Perform one
bj issue transition PROJ-42 "In Review"
```

## See also

- [`bj issue`](index.md)
