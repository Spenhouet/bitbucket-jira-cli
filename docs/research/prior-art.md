---
title: Prior art
sidebar_label: Prior art (research)
---

# Prior art research

Research backing the `bj` command design. Sources read: `gh` `--help` output
(v2.95, installed locally), the README/command references of three comparable
CLIs, and the official Atlassian Cloud REST API docs.

> This is an internal design document, not user-facing product docs.

## 1. GitHub `gh` — the UX spec

`bj` copies `gh`'s ergonomics: noun-first command groups, current-repo
inference from the git remote, `--json`/`--jq`/`--template` for scripting, and
`--web` to jump to the browser.

### Top-level (relevant subset)

| Group | Purpose |
|---|---|
| `gh auth` | Authenticate gh and git |
| `gh repo` | Manage repositories |
| `gh pr` | Manage pull requests |
| `gh issue` | Manage issues |
| `gh run` | View GitHub Actions workflow runs |
| `gh browse` | Open repo/PR/issue in the browser |
| `gh api` | Authenticated raw API request |

### `gh pr`

`create`, `list`, `status`, `checkout`, `checks`, `close`, `comment`, `diff`,
`edit`, `lock`, `merge`, `ready`, `reopen`, `revert`, `review`, `unlock`,
`update-branch`, `view`. A PR is addressable by number, URL, or head-branch name.

Key flags:
- `pr create`: `-t/--title`, `-b/--body`, `-B/--base`, `-H/--head`, `-d/--draft`, `-f/--fill` (title/body from commits), `-r/--reviewer`, `-a/--assignee`, `-l/--label`, `-w/--web`, `--dry-run`.
- `pr merge`: `-m/--merge`, `-s/--squash`, `-r/--rebase`, `-d/--delete-branch`, `--auto`, `--admin`.
- `pr list`: `-s/--state {open|closed|merged|all}`, `-B/--base`, `-H/--head`, `-a/--assignee`, `-l/--label`, `-S/--search`, `-L/--limit`, `--json`.
- `pr view`: `-c/--comments`, `-w/--web`, `--json`.

### `gh issue`

`create`, `list`, `status`, `close`, `comment`, `delete`, `develop` (linked
branches), `edit`, `lock`, `pin`, `reopen`, `transfer`, `unlock`, `view`.
`issue create` flags mirror `pr create` (`-t`, `-b`, `-l`, `-a`, `--type`, `-w`).
**In `bj`, `issue` maps to Jira, not Bitbucket** — see the mapping plan.

### `gh repo`

`create`, `list`, `clone`, `view`, `fork`, `edit`, `sync`, `set-default`,
`delete`, `rename`, `archive`, … Repo addressable as `OWNER/REPO` or URL.

### `gh run` (Actions)

`list`, `view`, `watch`, `cancel`, `rerun`, `delete`, `download`. This is the
analog for Bitbucket Pipelines.

### `gh browse` / `gh api`

`browse` opens the current repo/PR/issue/file in the browser (`-n` prints the
URL). `api` makes an authenticated request with `{owner}`/`{repo}` placeholders
resolved from the current repo, `-X/--method`, `-f`/`-F` fields, `--jq`,
`--paginate`, `--template`. `bj api` should mirror this for both backends.

## 2. `bb` — rbansal42/bitbucket-cli

Repo: <https://github.com/rbansal42/bitbucket-cli>. Deliberately modeled on
`gh` with near one-to-one parity. **Uses Bitbucket's built-in issue tracker,
not Jira** — the key reason `bj` exists.

Command tree:
- `bb auth` — `login`, `logout`, `status`
- `bb pr` — `list`, `view`, `create`, `merge`, `checkout`, `close`, `review`, `comment`, `diff`, `checks`
- `bb repo` — `list`, `view`, `clone`, `create`, `fork`, `delete`, `sync`, `set-default`
- `bb issue` — `list`, `view`, `create`, `edit`, `close`, `comment`, `delete` (Bitbucket-native issues)
- `bb pipeline` — `list`, `view`, `run`, `logs`, `steps`, `stop` (the `gh run` analog)
- `bb branch`, `bb workspace`, `bb project`, `bb snippet`, `bb browse`, `bb api`, `bb config`

Divergences from `gh` reflect Bitbucket's model: `bb pipeline` replaces
`gh run`, and an extra `workspace`/`project` layer accounts for Bitbucket's
workspace → project → repo hierarchy. **Takeaway for `bj`:** adopt `bb`'s
`pr`/`repo`/`pipeline` shape directly; take `issue` from Jira instead.

## 3. `jira` — ankitpokhrel/jira-cli

Repo: <https://github.com/ankitpokhrel/jira-cli>. The reference for mapping Jira
concepts to a CLI.

- `jira init` (interactive setup), `jira me`
- `jira issue` — `list`, `create`, `view`, `edit`, `assign`, `delete`, `move` (**= transition**), `link`/`unlink`/`link remote`, `clone`, `comment add`, `worklog add`
- `jira epic` — `list`, `create`, `add`, `remove`
- `jira sprint` — `list` (`--current`/`--prev`/`--next`), `add`
- `jira project` / `jira board` / `jira release` — `list`
- `jira open` — browser

Concept mapping learned here:
- **JQL:** `-q/--jql` for raw JQL, plus shorthand filters (`-s/--status`, `-a/--assignee`, `-t/--type`, `-l/--label`, `--created`, `--updated`).
- **Transitions** are exposed as `issue move`.
- **Sprints / epics / boards / worklogs** are Jira-only primitives with no `gh` counterpart.
- **Scripting output:** `--plain`, `--raw` (JSON), `--csv`, `--no-input` — echoes `gh --json`.

**Takeaway for `bj`:** model `bj issue` on `jira issue` (add `--jql`, transitions
via a `bj issue transition`/`move` verb, comments). Sprints/epics/boards are
out of scope for the MVP but the noun-verb slots are reserved.

## 4. atlassian-cli — omar16100/atlassian-cli

Repo: <https://github.com/omar16100/atlassian-cli>. **Correction to a common
assumption:** `atlassiancli.com` is the marketing/docs site for *this same
open-source project* (MIT, by Omar Shabab, unaffiliated with Atlassian) — there
is no separate commercial edition.

A unified Rust CLI spanning Jira, Confluence, Bitbucket, and JSM. Structure is
`atlassian-cli <product> <operation> [flags]`, e.g.:
- `atlassian-cli jira bulk transition --jql "…" --transition "Done" --dry-run`
- `atlassian-cli bitbucket pr merge myteam api-service 42 --strategy squash`

Diverges from `gh` in three deliberate ways: (1) a **product segment** prefix
(three levels deep) because it spans four products; (2) **automation-first**, not
interactive — bulk ops + `--dry-run` + JQL/CQL are headline features; (3)
positional workspace/repo/id args instead of git-remote inference.

**Takeaway for `bj`:** we intentionally reject the product-prefix (single
Bitbucket+Jira focus lets us stay two levels deep like `gh`) and keep git-remote
inference. Borrow its `--dry-run` safety idea for the auto-transition flow.

## 5. REST APIs and auth

### Bitbucket Cloud REST API v2.0

Base `https://api.bitbucket.org/2.0`. Path params `{workspace}`, `{repo_slug}`,
`{pull_request_id}`, `{pipeline_uuid}`, `{step_uuid}`.

Pull requests:
- List `GET /repositories/{workspace}/{repo_slug}/pullrequests`
- Create `POST …/pullrequests`
- Get `GET …/pullrequests/{id}`
- Update (title/description/**reviewers**/dest) `PUT …/pullrequests/{id}`
- Merge `POST …/pullrequests/{id}/merge`
- Decline `POST …/pullrequests/{id}/decline`
- Diff `GET …/pullrequests/{id}/diff`; Diffstat `GET …/pullrequests/{id}/diffstat`
- Approve `POST …/pullrequests/{id}/approve`; remove approval `DELETE …/approve`
- Request changes `POST …/pullrequests/{id}/request-changes`
- Comments `GET`/`POST …/pullrequests/{id}/comments`

There is **no "add reviewer" endpoint** — set the `reviewers` array in the
create/update body; read review state from the PR's `participants`/`reviewers`.

Repositories:
- Get `GET /repositories/{workspace}/{repo_slug}`
- List in workspace `GET /repositories/{workspace}` (`?q=`, `?role=`, `?sort=`, paginated via `next`)
- **Clone URLs** come from `repo.links.clone[]` (`name` = `"https"` or `"ssh"`); `links.html.href` is the web URL.

Pipelines (the `gh run` analog):
- List `GET …/pipelines`; Trigger `POST …/pipelines`; Get `GET …/pipelines/{uuid}`
- Stop `POST …/pipelines/{uuid}/stopPipeline`
- Steps `GET …/pipelines/{uuid}/steps`; Step `GET …/steps/{step_uuid}`; **Log** `GET …/steps/{step_uuid}/log`
- UUIDs are brace-wrapped; URL-encode the braces. Trigger body selects `target` (branch ref) and optional custom `selector` + `variables`.

### Jira Cloud REST API v3

Base `https://your-domain.atlassian.net/rest/api/3`. `{issueIdOrKey}` accepts
key (`PROJ-123`) or numeric id.

- **JQL search:** `POST /search/jql` (also `GET`). **The old `/search` was
  removed and returns `410 Gone` (deprecated 1 May 2025)** — build only against
  `/search/jql`. Pagination is **token-based** (`nextPageToken`), no `total`;
  use `POST /search/approximate-count` for counts. You must **explicitly request
  fields** (`fields: ["summary","status","assignee"]` or `["*all"]`).
- Get `GET /issue/{k}`; Create `POST /issue`; Edit `PUT /issue/{k}`; Delete `DELETE /issue/{k}`
- Comments `GET`/`POST /issue/{k}/comment`
- Transitions: list `GET /issue/{k}/transitions`; perform `POST /issue/{k}/transitions` with `{"transition":{"id":"…"}}` (IDs are workflow-specific — fetch first)
- Remote links: `GET`/`POST /issue/{k}/remotelink`, `DELETE …/remotelink/{linkId}`. Ideal for linking a Bitbucket PR URL to an issue; pass a stable `globalId` for idempotent upsert.
- **Bodies use ADF** (Atlassian Document Format) JSON in v3, not plain text — comment/description must be ADF documents.

### Auth — the two backends differ and cannot share a credential

A Bitbucket token will not authenticate against Jira and vice versa. `bj` must
store **two independent credentials**.

- **Bitbucket Cloud:** app passwords are **dead in 2026** (removal 28 Jul 2026).
  Use **scoped Atlassian API tokens** via Basic auth `base64(email:token)`, or
  **repository/workspace access tokens** via `Authorization: Bearer`. Scopes for
  `bj` (7): `read:user:bitbucket` (for `GET /user`, used by auth validation),
  `read:workspace:bitbucket` (list members for reviewer selection),
  `read:repository:bitbucket`, `read/write:pullrequest:bitbucket`,
  `read/write:pipeline:bitbucket`. Write does **not** imply read for granular
  API-token scopes — request both. `read:account` is **not** a Bitbucket
  API-token scope (it's a legacy OAuth scope); `write:repository` is not needed
  since `bj` only reads and clones repos.
- **Jira Cloud:** `bj` supports **two token modes** (chosen at login). *Site
  mode* — an **unscoped API token + Basic auth** `base64(email:token)` against
  the `*.atlassian.net` host (what jira-cli / go-jira use). *Gateway mode* — a
  **scoped API token**: scoped Jira tokens are only accepted on the
  `api.atlassian.com/ex/jira/{cloudId}` gateway (they 401 on the site host), so
  `bj` resolves the cloudId from `{site}/_edge/tenant_info` at login and targets
  the gateway. Covering scopes: `read:jira-work`, `write:jira-work`,
  `read:jira-user` (classic) — sufficient for issues, comments, transitions and
  remote links; fine-grained equivalents are `read/write:issue:jira`,
  `read:issue.transition:jira`, `write:comment:jira`,
  `read/write:issue.remote-link:jira` (note `issue.remote-link` with a dot —
  distinct from the internal `issue-link` scope). Write does not imply read;
  grant both.
- OAuth 2.0 (3LO) exists for multi-user distribution; overkill for a single-user
  CLI. The same Atlassian email may back both Basic credentials, but the token
  strings are distinct and separately revocable.

Sources: developer.atlassian.com (Bitbucket PR/Repositories/Pipelines/scopes,
Jira issue-search v3, CHANGE-2046), the three CLI repos above, and local
`gh --help`.
