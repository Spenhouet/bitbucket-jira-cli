---
title: bj variable set
---

# bj variable set

Set a pipeline variable (creates or replaces it).

## Synopsis

```
bj variable set [OPTIONS] KEY VALUE
```

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Variable name. _(required)_ |
| `VALUE` | Variable value. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `--secured` | Store as a secret (write-only). |
| `-R, --repo <text>` | WORKSPACE/REPO. |

## Examples

```bash
bj variable set DEPLOY_ENV production
bj variable set API_TOKEN s3cret --secured
```

## See also

- [`bj variable`](index.md)
