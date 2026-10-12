---
title: bj automation import
---

# bj automation import

Create a rule from an exported definition.

## Synopsis

```
bj automation import [OPTIONS] SOURCE
```

## Arguments

| Argument | Description |
| --- | --- |
| `SOURCE` | Rule definition file from `bj automation export`, or - for stdin. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-n, --name <text>` | Name for the new rule. |
| `--enable` | Create the rule enabled (default: disabled). |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
# Copy a rule: export, change it with jq, import it as a new rule
bj automation export 0192e5ac-0e25-71de-ba7b-d972e6a2049a -o weekly.json
jq '.rule.description = "Runs once a year"' weekly.json > yearly.json
bj automation import yearly.json --name "Yearly check"
```

## See also

- [`bj automation`](index.md)
