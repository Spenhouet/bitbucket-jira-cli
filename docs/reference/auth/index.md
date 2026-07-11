---
title: bj auth
sidebar_label: auth
---

# bj auth

Authenticate bj with Bitbucket and Jira.

## Synopsis

```
bj auth <command> [OPTIONS]
```

## Description

`bj` stores two independent credentials, one for Bitbucket and one for Jira, because the two products use separate API tokens. Tokens go to the OS keyring by default, or a 0600 file with `--insecure-storage`. See the [environment](../../guides/environment.md) guide for the `BJ_*_TOKEN` overrides.

## Commands

| Command | Description |
| --- | --- |
| [`login`](login.md) | Log in to Bitbucket and/or Jira with API tokens (Basic auth). |
| [`status`](status.md) | Show which backends are configured and validate the stored tokens. |
| [`logout`](logout.md) | Remove stored credentials for one or both backends. |
| [`token`](token.md) | Print the stored token for a backend (for scripting). |

## See also

- [`bj`](../index.md)
