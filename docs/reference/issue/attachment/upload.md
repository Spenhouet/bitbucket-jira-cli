---
title: bj issue attachment upload
---

# bj issue attachment upload

Attach local files to an issue.

## Synopsis

```
bj issue attachment upload [OPTIONS] KEY FILES
```

## Description

Attach local files to an issue, like `gh release upload`. Each file is uploaded on its own, and bj prints its name, size and the new attachment id. Every path is checked before the first upload. If Jira refuses a file, the error names it and lists the files that were already uploaded.

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Issue key. _(required)_ |
| `FILES` | Files to attach. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `--json` | Output raw JSON. |
| `-q, --jq <text>` | Filter JSON with a jq expression. |

## Examples

```bash
bj issue attachment upload PROJ-42 screenshot.png
bj issue attachment upload PROJ-42 build.log report.pdf --jq '.[].id'
```

## See also

- [`bj issue attachment`](index.md)
