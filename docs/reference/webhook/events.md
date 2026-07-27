---
title: bj webhook events
---

# bj webhook events

List the events a webhook can subscribe to.

## Synopsis

```
bj webhook events [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `-s, --subject <text>` | Subject type: repository or workspace. _(default: repository)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj webhook events
bj webhook events --subject workspace
```

## See also

- [`bj webhook`](index.md)
