---
title: Configuration
---

# Configuration

`bj` follows the same split the GitHub CLI uses: non-sensitive settings live in a
YAML file; secrets (API tokens) go to the OS keyring.

## Location

The config directory is `$BJ_CONFIG_DIR`, else `$XDG_CONFIG_HOME/bitbucket-jira-cli`,
else `~/.config/bitbucket-jira-cli`. Files are written with `0600` permissions.

- `config.yml`: non-sensitive settings (below).
- `credentials.yml`: only present if you logged in with `--insecure-storage`.

## `config.yml`

Written by [`bj auth login`](../reference/auth/login.md) (the `bitbucket.email`,
`jira.site` and `jira.email` fields) and
[`bj repo set-default`](../reference/repo/set-default.md) (the default
`bitbucket.workspace`); you can also edit it by hand. Inside a Bitbucket clone
the workspace is read from the `origin` remote, so setting a default is only
needed for commands run outside a clone (like `bj repo list`).

```yaml
version: 1
git_protocol: https          # https | ssh, used by `bj repo clone`
bitbucket:
  workspace: myteam          # default workspace when not in a clone
  email: you@example.com     # Atlassian account email (basic auth)
  auth_mode: basic           # basic (email:token) | bearer (access token)
jira:
  site: https://your-domain.atlassian.net
  email: you@example.com
  auth_mode: site            # site (unscoped) | gateway (scoped API token)
  cloud_id: null             # set automatically in gateway mode
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

1. Environment variable (`BJ_BITBUCKET_TOKEN` / `BJ_JIRA_TOKEN`), never persisted.
2. The OS keyring (service `bitbucket-jira-cli`).
3. `credentials.yml` (only if `--insecure-storage` was used).

Bitbucket and Jira use **separate** tokens; a token for one will not authenticate
the other. See [Environment](./environment.md) for the full variable list and
[`bj auth`](../reference/auth/index.md) for the login flow.

## Tokens

Both tokens are created at
[id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens).

### Bitbucket scoped API token

Use **"Create API token with scopes"**, app **Bitbucket**. For full command
coverage, grant all of these (Bitbucket's granular scopes do not imply each
other, so tick every box you want):

- `read:user:bitbucket`: the current-user check `bj auth login` runs
- `read:workspace:bitbucket`: list workspace members (reviewer selection)
- `read:repository:bitbucket`, `write:repository:bitbucket`,
  `admin:repository:bitbucket`, `delete:repository:bitbucket`
- `read:pullrequest:bitbucket`, `write:pullrequest:bitbucket`
- `read:pipeline:bitbucket`, `write:pipeline:bitbucket`, `admin:pipeline:bitbucket`
- `read:ssh-key:bitbucket`, `write:ssh-key:bitbucket`, `delete:ssh-key:bitbucket`
- `read:snippet:bitbucket`, `write:snippet:bitbucket`, `delete:snippet:bitbucket`

Which scope each command family needs:

| Commands | Scope |
| --- | --- |
| everyday reads, PRs, clone | `read:*`, `read/write:pullrequest`, `read:repository` |
| `repo create` / `edit` / `rename` / `fork` | `write:repository:bitbucket` |
| `ruleset list` (branch restrictions) | `admin:repository:bitbucket` |
| `repo delete` | `delete:repository:bitbucket` |
| `variable` (pipeline variables) | `admin:pipeline:bitbucket` |
| `ssh-key add` / `repo deploy-key add` | `write:ssh-key:bitbucket` |
| `ssh-key delete` / `deploy-key delete` | `delete:ssh-key:bitbucket` |
| `snippet list` / `view` | `read:snippet:bitbucket` |
| `snippet create` | `write:snippet:bitbucket` |
| `snippet delete` | `delete:snippet:bitbucket` |

The `delete:*` and `admin:*` scopes are separate on purpose: a token with only
`write:repository:bitbucket` can create and edit repos but not delete them.

### Jira: two token modes

`bj auth login` asks which you're using:

- **Unscoped (simplest)**: the plain **"Create API token"** button (no scope
  selection). `bj` sends it as Basic auth (email + token) against your
  `*.atlassian.net` site host, like the `jira` and `go-jira` CLIs. This becomes
  `jira.auth_mode: site` in `config.yml`.
- **Scoped (least privilege)**: **"Create API token with scopes"**, app
  **Jira**, scopes `read:jira-work`, `write:jira-work`, `read:jira-user`, and
  `manage:jira-project`. Scoped Jira tokens are only accepted on Atlassian's
  `api.atlassian.com/ex/jira/{cloudId}` gateway (they 401 against the site host),
  so `bj` resolves your site's cloudId from `{site}/_edge/tenant_info` at login,
  stores it as `jira.cloud_id`, and targets the gateway. This becomes
  `jira.auth_mode: gateway`.

`write:jira-work` covers issue create/edit, comments, transitions and remote
issue links; `read:jira-work` covers search and reads; `read:jira-user` covers
the current-user check; `manage:jira-project` covers `bj release` (Jira
versions). Write does not imply read, so grant both.

`bj board` (agile boards/sprints) is the one exception: Atlassian rejects scoped
API tokens on the Jira agile API ("Unauthorized; scope does not match"),
regardless of which agile scopes you tick. It works only with an **unscoped**
Jira token (`jira.auth_mode: site`), which is not scope-limited. Verified
against a scoped token carrying `read:board-scope:jira-software`,
`read:sprint:jira-software`, and `read:project:jira` — still rejected.
