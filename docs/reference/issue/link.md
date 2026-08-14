---
title: bj issue link
---

# bj issue link

Link an issue to another issue, or attach a URL to it.

## Synopsis

```
bj issue link [OPTIONS] [KEY] [TARGET]
```

## Description

Link an issue to another issue, or attach a URL to it. A target that looks like an issue key creates an issue link; anything starting with `http://` or `https://` is attached as a remote link, using the URL as its `globalId` so re-linking the same URL updates it instead of adding a duplicate. `--type` takes the link type name or either direction's wording: `--type blocks` reads *KEY blocks TARGET*, `--type 'is blocked by'` reads *KEY is blocked by TARGET* and swaps the two issues in the payload. Without `--type` the type is picked interactively, or defaults to `Relates` when there is no terminal.

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Issue key (default: from branch). |
| `TARGET` | Issue key or URL to link the issue to. |

## Options

| Option | Description |
| --- | --- |
| `-t, --type <text>` | Link type or wording, e.g. 'Blocks', 'blocks', 'is blocked by'. |
| `--title <text>` | Title for a URL link (default: the URL). |

## Examples

```bash
# PROJ-42 blocks PROJ-43
bj issue link PROJ-42 PROJ-43 --type blocks

# The other direction: PROJ-42 is blocked by PROJ-43
bj issue link PROJ-42 PROJ-43 --type 'is blocked by'

# Attach a URL to the branch's issue
bj issue link https://example.com/design --title 'Design doc'
```

## See also

- [`bj issue`](index.md)
