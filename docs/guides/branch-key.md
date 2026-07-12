---
title: Branch-key workflow
---

# Branch-key workflow

The feature that sets `bj` apart from a plain Bitbucket client: your current git
branch carries a Jira key, and `bj` uses it to link pull requests to tickets and
drive Jira transitions automatically, with no ticket IDs typed by hand.

## The parsing rule

`bj` scans the current branch name for a Jira key. The default pattern is
case-tolerant and matches `PROJECT-NUMBER`:

```
([A-Za-z][A-Za-z0-9]+-\d+)
```

| Branch | Key |
| --- | --- |
| `feature/PROJ-42-add-widget` | `PROJ-42` |
| `PROJ-42` | `PROJ-42` |
| `bugfix/abc-7-hotfix` | `ABC-7` |
| `main` | _(none)_ |

The first match wins and the key is upper-cased. Configure it under
`branch_key` in `config.yml` (see [Configuration](./configuration.md)):

- `pattern`: override the regex.
- `project_prefixes`: an allow-list (e.g. `["PROJ", "ABC"]`) so stray matches
  like `utf-8` are ignored.
- `enabled`: set to `false` to turn off all auto-linking and transitions.

## `bj pr create`

On a branch with a key, [`bj pr create`](../reference/pr/create.md):

1. Reads the key (e.g. `PROJ-42`).
2. Fills the PR **title** from the Jira ticket summary (`PROJ-42: <summary>`)
   unless you pass `--title`, and references the key in the body.
3. Creates the pull request.
4. **Links** the PR URL to the issue as a Jira remote link.
5. **Transitions** the ticket to the configured in-progress state
   (`transitions.on_pr_create`, default `In Progress`).

Use `--dry-run` to preview the title/link/transition without writing anything,
or `--no-jira` to create a plain PR with no Jira side effects.

## `bj pr merge`

[`bj pr merge`](../reference/pr/merge.md) reads the key from the PR's source
branch and, after a successful merge, transitions the ticket to the configured
done state (`transitions.on_pr_merge`, default `Done`).

## Graceful degradation

If no key is found, Jira is not configured, or `branch_key.enabled` is `false`,
`bj` behaves like a plain Bitbucket client. It creates or merges the PR and
skips every Jira step, printing a one-line note that no ticket was linked.
Transition **names** are resolved to workflow **IDs** at runtime, so per-project
Jira workflows work without any hardcoding.
