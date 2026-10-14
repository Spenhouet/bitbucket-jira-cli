---
title: bj issue attachment list
---

# bj issue attachment list

List the attachments on an issue.

## Synopsis

```
bj issue attachment list [OPTIONS] [KEY]
```

## Description

List the files attached to an issue with their id, name, size and type. With no key, the key is read from the current git branch.

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Issue key (default: from branch). |

## Options

| Option | Description |
| --- | --- |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj issue attachment list PROJ-42
bj issue attachment list PROJ-42 --jq '.[].filename'
```

## See also

- [`bj issue attachment`](index.md)
