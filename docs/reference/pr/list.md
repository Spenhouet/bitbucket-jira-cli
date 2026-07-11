---
title: bj pr list
sidebar_label: list
---

# bj pr list

List pull requests in a repository.

## Synopsis

```
bj pr list [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `-s, --state <text>` | open|merged|declined|all. _(default: open)_ |
| `-H, --head <text>` | Filter by source branch. |
| `-L, --limit <integer>` | Max results. _(default: 30)_ |
| `-R, --repo <text>` | Target repo as WORKSPACE/REPO. |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |
| `-w, --web` | Open in the browser. |

## Examples

```bash
bj pr list
bj pr list --state merged --limit 50
bj pr list --json | jq '.[].title'
```

## See also

- [`bj pr`](index.md)
