---
title: bj pr
---

# bj pr

Manage Bitbucket pull requests.

## Synopsis

```
bj pr <command> [OPTIONS]
```

## Commands

| Command | Description |
| --- | --- |
| [`create`](create.md) | Open a pull request; auto-link and transition the branch's Jira ticket. |
| [`edit`](edit.md) | Edit an open pull request's title, description, target branch or reviewers. |
| [`list`](list.md) | List pull requests in a repository. |
| [`view`](view.md) | View a pull request. |
| [`diff`](diff.md) | View the changes in a pull request. |
| [`status`](status.md) | Show open PRs relevant to you (authored or reviewing). |
| [`checkout`](checkout.md) | Check out a pull request's source branch locally. |
| [`merge`](merge.md) | Merge a pull request; transition the linked Jira ticket to done. |
| [`review`](review.md) | Approve, request changes on, or unapprove a pull request. |
| [`comment`](comment.md) | Comment on a PR: top-level, inline (--file/--line), reply (--reply-to), or manage. |
| [`close`](close.md) | Decline (close) a pull request. |
| [`checks`](checks.md) | Show the build/commit statuses (CI checks) for a pull request. |
| [`ready`](ready.md) | Mark a draft pull request as ready for review (or --undo back to draft). |
| [`reopen`](reopen.md) | Reopen a declined pull request by opening a fresh one from the same branches. |
| [`task`](task.md) | Manage pull-request tasks (checklist items). |

## See also

- [`bj`](../index.md)
