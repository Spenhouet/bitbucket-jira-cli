---
title: bj issue unlink
---

# bj issue unlink

Remove a link from an issue.

## Synopsis

```
bj issue unlink [OPTIONS] [KEY] [TARGET]
```

## Description

Remove a link from an issue. The target can be the linked issue's key, the attached URL, or a link id from `bj issue links`.

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Issue key (default: from branch). |
| `TARGET` | Linked issue key, URL, or link id (see `issue links`). |

## Options

| Option | Description |
| --- | --- |
| `-y, --yes` | Skip the confirmation prompt. |

## Examples

```bash
bj issue unlink PROJ-42 PROJ-43
bj issue unlink PROJ-42 https://example.com/design --yes
```

## See also

- [`bj issue`](index.md)
