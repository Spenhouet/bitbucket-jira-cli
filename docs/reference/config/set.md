---
title: bj config set
sidebar_label: set
---

# bj config set

Set a configuration value (validated against the schema).

## Synopsis

```
bj config set [OPTIONS] KEY VALUE
```

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Dotted key, e.g. git_protocol. _(required)_ |
| `VALUE` | New value. _(required)_ |

## Examples

```bash
bj config get git_protocol
bj config set bitbucket.workspace myteam
```

## See also

- [`bj config`](index.md)
