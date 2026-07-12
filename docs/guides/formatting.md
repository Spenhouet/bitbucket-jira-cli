---
title: Formatting output
---

# Formatting output

Read commands (`list`, `view`, `status`, and friends) render a human-friendly
table or summary by default. For scripting, two flags mirror the GitHub CLI.

## `--json`

Pass `--json` to emit the raw backend response as JSON instead of the rendered
view:

```bash
bj pr list --json
bj issue view PROJ-42 --json
```

Unlike `gh`, `--json` takes no field list. It prints the full JSON object or
array as returned by the Bitbucket or Jira API. Pipe it into a tool of your
choice, or use `--jq` below.

## `--jq` / `-q`

Filter the JSON with a [jq](https://jqlang.github.io/jq/manual/) expression:

```bash
bj pr list --jq '.[].title'
bj issue list --jq '.[] | .key + " " + .fields.summary'
```

> **Note:** unlike `gh` (which embeds a jq engine), `bj --jq` shells out to the
> `jq` binary, so `jq` must be installed and on your `PATH`. If it is missing,
> `bj` prints a clear error.

When `--jq` is given, `--json` is implied. There is currently no `--template`
flag; use `--jq` for output shaping.

## Colors

`bj` uses [rich](https://rich.readthedocs.io/) for rendering. Set `NO_COLOR` to
any value to disable ANSI colors (see [Environment](./environment.md)).
