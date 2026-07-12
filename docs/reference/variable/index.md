---
title: bj variable
sidebar_label: variable
---

# bj variable

Manage Bitbucket Pipelines variables (use --secured for secrets).

## Synopsis

```
bj variable <command> [OPTIONS]
```

## Description

Bitbucket Pipelines variables. Bitbucket models secrets and plaintext variables as one resource with a `secured` flag, so `--secured` covers what `gh secret` does.

## Commands

| Command | Description |
| --- | --- |
| [`list`](list.md) | List a repository's pipeline variables. |
| [`set`](set.md) | Set a pipeline variable (creates or replaces it). |
| [`delete`](delete.md) | Delete a pipeline variable by name. |

## See also

- [`bj`](../index.md)
