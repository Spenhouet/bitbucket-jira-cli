---
title: bj release create
---

# bj release create

Create a version on a project.

## Synopsis

```
bj release create [OPTIONS] NAME
```

## Arguments

| Argument | Description |
| --- | --- |
| `NAME` | Version name, e.g. '1.2.0'. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-p, --project <text>` | Project key. _(required)_ |
| `-d, --description <text>` |  |
| `--release-date <text>` | YYYY-MM-DD. |
| `--released` | Create already released. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## See also

- [`bj release`](index.md)
