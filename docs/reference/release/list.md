---
title: bj release list
---

# bj release list

List a project's versions.

## Synopsis

```
bj release list [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `-p, --project <text>` | Project key. _(required)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj release list --project PROJ
bj release create 1.2.0 --project PROJ --release-date 2026-01-31
bj release release 10000
```

## See also

- [`bj release`](index.md)
