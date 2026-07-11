---
title: bj auth login
sidebar_label: login
---

# bj auth login

Log in to Bitbucket and/or Jira with API tokens (Basic auth).

## Synopsis

```
bj auth login [OPTIONS]
```

## Options

| Option | Description |
| --- | --- |
| `--bitbucket` | Only configure Bitbucket. |
| `--jira` | Only configure Jira. |
| `--insecure-storage` | Store tokens in a plaintext file (0600) instead of the OS keyring. |
| `--with-token` | Read one token from stdin (requires exactly one of --bitbucket/--jira). |

## Examples

```bash
# Log in to both backends interactively
bj auth login

# Only Jira; read the token from stdin (non-interactive)
printf "%s" "$JIRA_TOKEN" | bj auth login --jira --with-token
```

## See also

- [`bj auth`](index.md)
