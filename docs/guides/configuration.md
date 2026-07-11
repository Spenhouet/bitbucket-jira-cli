---
sidebar_position: 2
title: Configuration
---

# Configuration

`bj` follows the same split the GitHub CLI uses: non-sensitive settings live in a
YAML file; secrets (API tokens) go to the OS keyring.

## Location

The config directory is `$BJ_CONFIG_DIR`, else `$XDG_CONFIG_HOME/bitbucket-jira-cli`,
else `~/.config/bitbucket-jira-cli`. Files are written with `0600` permissions.

- `config.yml` — non-sensitive settings (below).
- `credentials.yml` — only present if you logged in with `--insecure-storage`.

## `config.yml`

Written by [`bj auth login`](../reference/auth/login.md) (the `bitbucket.email`,
`jira.site` and `jira.email` fields) and
[`bj repo set-default`](../reference/repo/set-default.md) (the default
`bitbucket.workspace`); you can also edit it by hand. Inside a Bitbucket clone
the workspace is read from the `origin` remote, so setting a default is only
needed for commands run outside a clone (like `bj repo list`).

```yaml
version: 1
git_protocol: https          # https | ssh — used by `bj repo clone`
bitbucket:
  workspace: myteam          # default workspace when not in a clone
  email: you@example.com     # Atlassian account email (basic auth)
  auth_mode: basic           # basic (email:token) | bearer (access token)
jira:
  site: https://your-domain.atlassian.net
  email: you@example.com
branch_key:
  enabled: true
  pattern: ([A-Za-z][A-Za-z0-9]+-\d+)
  project_prefixes: []       # e.g. [PROJ, ABC] to ignore stray matches
transitions:
  on_pr_create: In Progress  # ticket state after `bj pr create`
  on_pr_merge: Done          # ticket state after `bj pr merge`
```

## Token storage

`bj` never writes tokens to `config.yml`. At read time it resolves each backend's
token in this order:

1. Environment variable (`BJ_BITBUCKET_TOKEN` / `BJ_JIRA_TOKEN`) — never persisted.
2. The OS keyring (service `bitbucket-jira-cli`).
3. `credentials.yml` (only if `--insecure-storage` was used).

Bitbucket and Jira use **separate** tokens; a token for one will not authenticate
the other. See [Environment](./environment.md) for the full variable list and
[`bj auth`](../reference/auth/index.md) for the login flow.

## Tokens

Both tokens are created at
[id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens).

### Bitbucket — scoped API token

Use **"Create API token with scopes"**, app **Bitbucket**, and grant these seven:

- `read:user:bitbucket` — required for the current-user check `bj auth login` runs
- `read:workspace:bitbucket` — list workspace members (reviewer selection)
- `read:repository:bitbucket` — view/list repos, read clone URLs, clone
- `read:pullrequest:bitbucket` and `write:pullrequest:bitbucket`
- `read:pipeline:bitbucket` and `write:pipeline:bitbucket`

For granular API-token scopes, **write does not imply read** — tick both boxes
for Pull Requests and Pipelines. `write:repository` is not needed (`bj` only
reads and clones repositories).

### Jira — unscoped API token

Use the plain **"Create API token"** button (no scope selection). `bj` sends it
as Basic auth (email + token) against your `*.atlassian.net` site, the same as
the `jira` and `go-jira` CLIs.

Do **not** use a *scoped* Jira token: scoped tokens are only accepted on
Atlassian's `api.atlassian.com/ex/jira/{cloudId}` gateway, which `bj` does not
target — they return 401 against the site host. (If `bj` later adds gateway
support, the equivalent scopes would be `read:jira-work`, `write:jira-work`,
`read:jira-user`.)
