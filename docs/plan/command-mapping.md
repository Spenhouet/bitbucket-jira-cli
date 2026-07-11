---
title: Command mapping plan
sidebar_label: Command mapping (plan)
---

# `bj` command mapping plan

Design plan for the `bj` command surface. Maps every relevant `gh` command to a
proposed `bj` equivalent, defines the branch-key workflow, and lists the open
decisions to resolve before coding. Backed by [prior-art research](../research/prior-art.md).

> **Status: awaiting review.** No feature code is written until this plan is
> approved. `issue` commands target **Jira**; `pr`/`repo`/`pipeline` target
> **Bitbucket**.

Legend for the **Backend** column: **BB** = Bitbucket Cloud API,
**Jira** = Jira Cloud API, **git** = local git, **both** = spans both APIs.
Bitbucket base `https://api.bitbucket.org/2.0`, Jira base `…/rest/api/3`.
`{ws}` = workspace, `{repo}` = repo_slug, `{id}` = pull_request_id, `{k}` = issue key.

## 1. Command mapping table

### auth

| `gh` | `bj` | Backend | Endpoint(s) | Notes |
|---|---|---|---|---|
| `gh auth login` | `bj auth login` | both | validate via `GET /user` (BB), `GET /myself` (Jira) | Prompts for **two** credentials: Bitbucket token + Jira token/site. Stores both. |
| `gh auth status` | `bj auth status` | both | same validation calls | Reports each backend independently (one can be configured without the other). |
| `gh auth logout` | `bj auth logout [--backend bitbucket\|jira]` | local | — | Clears stored creds; per-backend or both. |
| `gh auth token` | `bj auth token --backend …` | local | — | Print the stored token for scripting. |

### repo

| `gh` | `bj` | Backend | Endpoint(s) | Notes |
|---|---|---|---|---|
| `gh repo view` | `bj repo view [{ws}/{repo}]` | BB | `GET /repositories/{ws}/{repo}` | Defaults to the repo inferred from the git remote. |
| `gh repo list` | `bj repo list [{ws}]` | BB | `GET /repositories/{ws}` | `--role`, `-q/--query` (Bitbucket `q=`), `-L/--limit` (paginate `next`). |
| `gh repo clone` | `bj repo clone {ws}/{repo}` | BB + git | `GET /repositories/{ws}/{repo}` then `git clone` | Clone URL from `repo.links.clone[] name="https"\|"ssh"`. |
| `gh repo set-default` | `bj repo set-default` | local | — | Persist the default workspace/repo for this directory. |

### pr → Bitbucket pull requests

| `gh` | `bj` | Backend | Endpoint(s) | Notes |
|---|---|---|---|---|
| `gh pr create` | `bj pr create` | BB (+Jira) | `POST …/pullrequests` | **Branch-key aware** (see §2): auto-fills title/body from the Jira ticket, links them, transitions the ticket. `-t/-b/-B/-H/-d/-r/-w/--fill/--dry-run`. |
| `gh pr list` | `bj pr list` | BB | `GET …/pullrequests` | `-s/--state {open\|merged\|declined\|all}` (BB uses OPEN/MERGED/DECLINED/SUPERSEDED), `-H/--head`, `-L/--limit`. |
| `gh pr view` | `bj pr view [id]` | BB | `GET …/pullrequests/{id}` (+`/comments` with `-c`) | Default target = PR whose source branch is the current branch. |
| `gh pr diff` | `bj pr diff [id]` | BB | `GET …/pullrequests/{id}/diff` (`/diffstat` for `--stat`) | Raw unified diff. |
| `gh pr checkout` | `bj pr checkout <id>` | BB + git | `GET …/pullrequests/{id}` then `git fetch`/`checkout` | Checks out the PR's source branch. |
| `gh pr merge` | `bj pr merge [id]` | BB (+Jira) | `POST …/pullrequests/{id}/merge` | **Branch-key aware**: transitions the linked ticket to Done on success. `-s/--squash` (BB `merge_strategy`), `-d/--delete-branch`, `--merge`, `--fast-forward`. |
| `gh pr review` | `bj pr review [id]` | BB | `POST …/approve` / `DELETE …/approve` / `POST …/request-changes` | `--approve`, `--request-changes`. BB has no "comment review" body — use `pr comment`. |
| `gh pr comment` | `bj pr comment [id] -b …` | BB | `POST …/pullrequests/{id}/comments` | Inline comments (with `path`/`line`) deferred past MVP. |
| `gh pr close` | `bj pr close [id]` | BB | `POST …/pullrequests/{id}/decline` | Bitbucket "decline" == close. |
| `gh pr status` | `bj pr status` | BB | `GET …/pullrequests?q=…` filtered by current user | "PRs relevant to me": authored + reviewing. |

### issue → **Jira** issues (not Bitbucket)

| `gh` | `bj` | Backend | Endpoint(s) | Notes |
|---|---|---|---|---|
| `gh issue list` | `bj issue list` | Jira | `POST /search/jql` | `-q/--jql` raw JQL + shorthand `-s/--status`, `-a/--assignee`, `-t/--type`, `-l/--label`. Token pagination; must request `fields`. |
| `gh issue view` | `bj issue view <KEY>` | Jira | `GET /issue/{k}` | `-c/--comments` → `GET /issue/{k}/comment`. Default `<KEY>` = branch key (§2). |
| `gh issue create` | `bj issue create` | Jira | `POST /issue` | `-t/--type`, `-s/--summary`, `-b/--body`, `-P/--project`. Body serialized to **ADF**. |
| `gh issue edit` | `bj issue edit <KEY>` | Jira | `PUT /issue/{k}` | Field updates. |
| `gh issue close` | `bj issue close <KEY>` / `bj issue transition <KEY> <state>` | Jira | `GET`+`POST /issue/{k}/transitions` | Jira has no generic "close" — it's a **transition**. `close` is sugar for transitioning to the configured done state; `transition` is the general verb (jira-cli's `move`). |
| `gh issue comment` | `bj issue comment <KEY> -b …` | Jira | `POST /issue/{k}/comment` | Body → ADF. |
| — | `bj issue transition <KEY> [state]` | Jira | `GET`/`POST /issue/{k}/transitions` | Lists available transitions when `state` omitted. |

### pipeline → Bitbucket Pipelines (the `gh run` analog)

| `gh` | `bj` | Backend | Endpoint(s) | Notes |
|---|---|---|---|---|
| `gh run list` | `bj pipeline list` | BB | `GET …/pipelines` | `--branch`, `-L/--limit`. |
| `gh run view` | `bj pipeline view <uuid>` | BB | `GET …/pipelines/{uuid}` (+`/steps`) | Brace-wrapped UUID, URL-encoded. |
| `gh run view --log` | `bj pipeline logs <uuid> [--step …]` | BB | `GET …/pipelines/{uuid}/steps/{step_uuid}/log` | Supports HTTP `Range` for large logs. |
| `gh run rerun` / (trigger) | `bj pipeline run` | BB | `POST …/pipelines` | Body: `target` (branch ref) + optional custom `selector`/`variables`. Defaults ref to current branch. |
| `gh run cancel` | `bj pipeline stop <uuid>` | BB | `POST …/pipelines/{uuid}/stopPipeline` | |

### cross-cutting

| `gh` | `bj` | Backend | Endpoint(s) | Notes |
|---|---|---|---|---|
| `gh browse` | `bj browse [pr\|issue\|repo]` | local | — | Opens the web URL. `bj browse` (repo), `bj browse pr` (current-branch PR), `bj browse issue` (branch-key ticket). `-n` prints URL. |
| `gh api` | `bj api <path> [--backend bitbucket\|jira]` | BB/Jira | any | Authenticated raw request. `-X`, `-f`/`-F`, `--jq`, `--paginate`. Needs a `--backend` selector since there are two hosts (default: bitbucket). |

## 2. The branch-key workflow (killer feature)

The current git branch carries a Jira key. `bj` extracts it and uses it to link
and transition tickets automatically.

### Parsing rule

Default regex (case-insensitive), applied to the current branch name:

```
([A-Z][A-Z0-9]+-\d+)
```

Examples: `feature/PROJ-42-add-widget` → `PROJ-42`; `PROJ-42` → `PROJ-42`;
`bugfix/ABC-7_hotfix` → `ABC-7`. If multiple keys match, the **first** wins. If
none match, key-dependent behavior degrades gracefully (see below).

Configurable via `config.branch_key`:
- `pattern` — override the regex.
- `project_prefixes` — optional allow-list (e.g. `["PROJ","ABC"]`) so stray
  matches like `UTF-8` are ignored.
- `enabled` — master switch to disable all auto-linking/transitioning.

### `bj pr create` flow

1. Resolve branch key `K` (e.g. `PROJ-42`).
2. If `K` found and Jira configured: `GET /issue/{K}` → use the issue summary as
   the **default PR title** (`[PROJ-42] <summary>`) and a body template
   referencing the ticket. `-t`/`-b` flags override.
3. `POST …/pullrequests` to create the PR (source = current branch).
4. **Link**: `POST /issue/{K}/remotelink` with the PR URL + title and a stable
   `globalId` (e.g. the PR URL) for idempotent upsert.
5. **Transition**: move `K` to the configured *in-progress/in-review* state via
   `GET`+`POST /issue/{K}/transitions` (skip if already there).
6. `--dry-run` prints the intended title/body/link/transition without writing;
   `--no-jira` skips steps 2/4/5.

### `bj pr merge` flow

1. Resolve the PR for the current branch (or explicit id) and its linked key `K`.
2. `POST …/pullrequests/{id}/merge`.
3. On success, transition `K` to the configured **done** state
   (`POST /issue/{K}/transitions`).
4. `--no-jira` / `--dry-run` honored as above.

### Degradation

No key found, or Jira not configured, or `enabled:false` → `bj` behaves like a
plain Bitbucket client (create/merge the PR, skip all Jira steps) and prints a
one-line note that no ticket was linked. Transition names are configurable
because Jira workflows are per-project (transition **IDs** are fetched at
runtime, never hardcoded).

## 3. Decision checkpoint — RESOLVED

### D1 — Config & auth storage → **mirror `gh`** ✅

Follow exactly how the official `gh` CLI stores config and secrets:

- **Config dir:** `$BJ_CONFIG_DIR`, else `$XDG_CONFIG_HOME/bitbucket-jira-cli`
  (default `~/.config/bitbucket-jira-cli`). Files `0600`, dir `0700`.
- **`config.yml`** — non-sensitive only (like gh's `config.yml`): schema
  `version`, `git_protocol`, `editor`, `pager`, `browser`, output prefs, plus
  bj-specific `bitbucket.workspace`, `jira.site`, `jira.email`,
  `bitbucket.email`, `branch_key`, `transitions`. **No tokens.**
- **Tokens → OS keyring by default** (Python `keyring`, same backends gh uses:
  libsecret / Keychain / Windows Cred Manager). Service `bitbucket-jira-cli`,
  entries `bitbucket` and `jira`.
- **`--insecure-storage`** on `bj auth login` writes tokens to
  `credentials.yml` (`0600`) instead — gh's `hosts.yml oauth_token` analog.
- **Env overrides** `BJ_BITBUCKET_TOKEN` / `BJ_JIRA_TOKEN` take precedence and
  are never persisted (gh's `GH_TOKEN` behavior).
- Read precedence: env → keyring → `credentials.yml`.

Two independent credential slots (Bitbucket + Jira) since tokens can't be
shared. Login is an **API-token flow** (email + scoped token, Basic auth) — the
Atlassian-recommended path for CLIs — not browser OAuth.

### D2 — Issues → **Jira-only** ✅

`bj issue` targets Jira exclusively. Bitbucket's native tracker is not exposed.

### D3 — Scope → **no MVP; full `gh` mirror** ✅

Implement the complete command surface up front (every row in §1), verify it
mirrors `gh`, and test every command live against real Bitbucket + Jira once
auth is in place. No phased slice.

### D4 — Misc → **resolved** ✅

- **HTTP client:** `httpx` **async everywhere possible**; Typer commands wrap
  coroutines with a small `run()` helper.
- **Output:** `rich` tables by default, `--json`/`--jq`/`--template` for
  scripting (mirror `gh`).
- **Repo inference:** parse the `origin` git remote → `{workspace}/{repo_slug}`;
  Bitbucket Cloud (`bitbucket.org`) only for v1.
- **ADF:** accept Markdown/plain text from the user, convert to a minimal ADF
  document for Jira v3 bodies.

## 4. Build order (full implementation)

Not a phased MVP — the whole surface ships. Build order is just dependency
sequencing; auth lands first so live testing can begin.

**Foundation**
1. Config model + `config.yml` load/save, XDG paths, `0600` perms.
2. Auth store: keyring + `--insecure-storage` fallback + env resolution.
3. Async httpx clients: Bitbucket (Basic/Bearer) + Jira (Basic), error handling, pagination.
4. Git utils: current branch, `origin` → `{workspace}/{repo_slug}`, branch-key parser (§2).
5. ADF converter; shared `rich`/JSON output helpers; `run()` async wrapper.

**Auth** — `bj auth login` / `status` / `logout` / `token` (validate both backends). *← log in here.*

**Full command surface** (all of §1, tested live):
- `bj pr` — `create`, `list`, `view`, `diff`, `checkout`, `merge`, `review`, `comment`, `close`, `status` (branch-key on `create`/`merge`).
- `bj issue` — `list` (JQL), `view`, `create`, `edit`, `close`, `comment`, `transition`.
- `bj repo` — `view`, `list`, `clone`, `set-default`.
- `bj pipeline` — `list`, `view`, `logs`, `run`, `stop`.
- `bj browse`, `bj api`.

**Verification** — exercise every command against real Bitbucket + Jira; confirm ergonomic parity with `gh`.
