---
title: bj issue attachment download
---

# bj issue attachment download

Download issue attachments (all of them unless filtered).

## Synopsis

```
bj issue attachment download [OPTIONS] [KEY]
```

## Description

Download files attached to an issue, like `gh release download`. Without a filter every attachment is saved into `--dir` under its own name. Pick files with `--name`, `--pattern` or `--id`, or write a single file to `--output` (`-` writes it to stdout). An existing file stops the download unless you pass `--clobber` or `--skip-existing`.

## Arguments

| Argument | Description |
| --- | --- |
| `KEY` | Issue key (default: from branch). |

## Options

| Option | Description |
| --- | --- |
| `-n, --name <text>` | Download attachments with this file name (repeatable). |
| `-p, --pattern <text>` | Download attachments matching a glob (repeatable). |
| `--id <text>` | Download the attachment with this id (repeatable). |
| `-D, --dir <path>` | Directory to download files into. _(default: .)_ |
| `-O, --output <text>` | File to write a single attachment to ('-' for stdout). |
| `--clobber` | Overwrite existing files of the same name. |
| `--skip-existing` | Skip files that already exist. |

## Examples

```bash
# Download every attachment into the current directory
bj issue attachment download PROJ-42
bj issue attachment download PROJ-42 --pattern '*.png' --dir screenshots
bj issue attachment download PROJ-42 --id 10001 --output design.png
```

## See also

- [`bj issue attachment`](index.md)
