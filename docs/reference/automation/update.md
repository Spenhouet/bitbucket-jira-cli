---
title: bj automation update
---

# bj automation update

Change an existing rule to match an exported definition.

## Synopsis

```
bj automation update [OPTIONS] UUID
```

## Arguments

| Argument | Description |
| --- | --- |
| `UUID` | Rule UUID (see `bj automation list`). _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-i, --input <text>` | Rule definition file from `bj automation export`, or - for stdin. _(required)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
# Change a rule in place: export, change it with jq, update it
bj automation export 0192e5ac-0e25-71de-ba7b-d972e6a2049a -o rule.json
jq '.rule.description = "Runs once a month"' rule.json > changed.json
bj automation update 0192e5ac-0e25-71de-ba7b-d972e6a2049a --input changed.json
```

## See also

- [`bj automation`](index.md)
