---
sidebar_position: 5
title: Exit codes
---

# Exit codes

`bj` uses conventional process exit codes so you can branch on them in scripts.

| Code | Meaning |
| --- | --- |
| `0` | The command completed successfully. |
| `1` | The command failed. A backend rejected the request, you are not logged in, the current directory is not a Bitbucket repo, no Jira key was found, or a validation check failed. `bj` prints a one-line `error:` message (no traceback). |
| `2` | Usage error: an unknown command, a missing required argument, or an invalid option. This comes from the CLI parser and is accompanied by usage help. |

Note the difference from the GitHub CLI: `gh` uses exit code `4` for
authentication problems, whereas `bj` reports "not logged in" as a normal
failure with exit code `1`. A command may occasionally surface other codes from
an underlying tool (for example a non-zero `git clone` during
[`bj repo clone`](../reference/repo/clone.md)).
