---
title: bj automation list
---

# bj automation list

List automation rules (name, UUID, state, scope).

## Synopsis

```
bj automation list [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `-s, --state {enabled|disabled}` | Only rules in this state. |
| `-p, --project <text>` | Only rules scoped to this project (key or id). |
| `--trigger <text>` | Only rules with this trigger type, e.g. jira.issue.event.trigger:created. |
| `-L, --limit <integer>` | Maximum number of rules. _(default: 1000)_ |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj automation list --project PROJ --state enabled
bj automation list --json | jq -r '.[] | [.uuid, .name] | @tsv'
```

## See also

- [`bj automation`](index.md)
