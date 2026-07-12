---
title: bj alias
sidebar_label: alias
---

# bj alias

Create command shortcuts.

## Synopsis

```
bj alias <command> [OPTIONS]
```

## Description

User-defined command shortcuts, stored in `config.yml` and expanded before dispatch. `bj alias set co 'pr checkout'` makes `bj co` work.

## Commands

| Command | Description |
| --- | --- |
| [`set`](set.md) | Create or update an alias. |
| [`list`](list.md) | List defined aliases. |
| [`delete`](delete.md) | Delete an alias. |

## See also

- [`bj`](../index.md)
