---
title: bj config
---

# bj config

Read and write bj configuration.

## Synopsis

```
bj config <command> [OPTIONS]
```

## Description

Read and write non-sensitive settings in `config.yml` using dotted keys (e.g. `bitbucket.workspace`). Values are validated against the schema.

## Commands

| Command | Description |
| --- | --- |
| [`list`](list.md) | Print all configuration keys and values. |
| [`get`](get.md) | Print a single configuration value. |
| [`set`](set.md) | Set a configuration value (validated against the schema). |

## See also

- [`bj`](../index.md)
