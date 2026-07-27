---
title: bj webhook list
---

# bj webhook list

List webhooks on a repository or workspace.

## Synopsis

```
bj webhook list [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `-R, --repo <text>` | WORKSPACE/REPO. |
| `-W, --workspace <text>` | Operate on a workspace's webhooks instead. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj webhook list
bj webhook list --workspace myteam
bj webhook list --json | jq '.[].url'
```

## See also

- [`bj webhook`](index.md)
