---
title: bj repo
sidebar_label: repo
---

# bj repo

Work with Bitbucket repositories.

## Synopsis

```
bj repo <command> [OPTIONS]
```

## Commands

| Command | Description |
| --- | --- |
| [`view`](view.md) | View a repository. |
| [`list`](list.md) | List repositories in a workspace. |
| [`clone`](clone.md) | Clone a repository locally (HTTPS uses your bj token automatically). |
| [`set-default`](set-default.md) | Store the default workspace used when not inside a clone. |
| [`create`](create.md) | Create a new repository (needs a token with repository write scope). |
| [`fork`](fork.md) | Fork a repository into a workspace. |
| [`delete`](delete.md) | Delete a repository (irreversible; needs repository admin scope). |
| [`edit`](edit.md) | Edit repository settings (description, visibility, name). |
| [`rename`](rename.md) | Rename a repository. |
| [`file`](file.md) | Print the contents of a file in the repository. |
| [`ls`](ls.md) | List files in a repository directory. |
| [`deploy-key`](deploy-key.md) | Manage repository access/deploy keys. |

## See also

- [`bj`](../index.md)
