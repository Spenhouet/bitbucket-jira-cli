---
title: bj issue links
---

# bj issue links

List an issue's links: related issues and attached URLs.

## Synopsis

```
bj issue links [OPTIONS] [KEY]
```

## Description

List an issue's links: related issues (with the relationship as Jira words it) and attached URLs. The `Id` column feeds `bj issue unlink`.

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
bj issue links PROJ-42
bj issue links --json | jq '.remoteLinks[].object.url'
```

## See also

- [`bj issue`](index.md)
