---
title: TUI parity review (bj vs gh)
---

# TUI / interaction review: `bj` vs `gh`

Comparison of `bj`'s interactive behavior against the GitHub CLI, across the
seven interaction areas gh implements. Internal design doc.

## Verdict

`bj` matches gh on **structured output** (tables, colorized state, `--json`) and
now on **auth login** (arrow-key select, masked token). It diverges sharply on
**everything else interactive**: no confirmations before destructive actions, no
prompting for missing input, no editor, no multiselect, no spinner, no pager.
The single most important gap is **destructive actions run with zero
confirmation** (`pr merge`, `pr close`, `pipeline stop`, `issue close`), and
`pr merge` silently defaults to a merge-commit instead of asking.

## Area-by-area

| # | Area | gh | bj today | Gap |
|---|---|---|---|---|
| 1 | Prompt for missing input | Prompts (title → body/editor → "What's next?" submit menu); errors `must provide --title … when not running interactively` | `pr create`: silently uses ticket summary or branch name as title, empty body. `issue create`/comments: single-line `typer.prompt`. No submit menu. | **Large** |
| 2 | Confirm destructive actions | `pr merge` submit menu; `issue/repo delete` type-to-confirm; `--yes` to skip | **None.** `pr merge`/`pr close`/`issue close`/`pipeline stop` execute immediately. No `--yes`. | **Large (safety)** |
| 3 | Editor for bodies | `MarkdownEditor` prompt, `(e) to launch $EDITOR`; `--editor` | None — single-line prompts only. | Medium |
| 4 | Selector widgets | select, **multiselect+search** (reviewers/labels/assignees), confirm, password | Only `auth login` (select/text/password). Reviewers via repeated `-r`. | Medium |
| 5 | Progress spinner | Spinner during API calls (`GH_SPINNER_DISABLED` for a11y) | None — commands sit silent during network I/O. | Medium |
| 6 | Output rendering | Tables + color + **relative timestamps**; `view` renders markdown (glamour); non-TTY → tab-separated; **pager** (`GH_PAGER`) | Tables + color (rich, `box=None`, auto-drops color when piped). No relative time. Plain-text bodies. `--json` for scripting. No pager for diff/logs. | Small–Medium |
| 7 | Non-TTY / a11y | `CanPrompt()` gate; `GH_PROMPT_DISABLED`; accessible prompter | questionary gates TTY for auth; other prompts (`typer.prompt`) can hang/EOF; no explicit non-interactive errors. | Medium |

## Prioritized recommendations

### P1 — safety + core parity (recommended now)
1. **Confirm destructive/mutating actions**, with `-y/--yes` to skip and
   auto-skip when non-interactive: `pr merge`, `pr close`, `pipeline stop`,
   `issue close`. Use `questionary.confirm`.
2. **`pr merge` merge-method prompt**: when no `--merge/--squash/--fast-forward`
   given and interactive, `select` the method; when non-interactive, error
   `a merge method is required when not running interactively` instead of
   silently defaulting to a merge commit.
3. **Prompt for missing required input in a TTY**, and print a clean
   `must provide --X when not running interactively` otherwise. Targets:
   `pr create` (title/body), `issue create` (project/summary).

### P2 — interaction polish
4. **Spinner** around network calls via `rich`'s `console.status("working…")`
   (respect `NO_COLOR`; textual fallback). Cheap, high perceived quality.
5. **Editor** for bodies: `--editor` flag + "(e) to open editor" on body
   prompts, using `click.edit()`; resolve `BJ_EDITOR`/`VISUAL`/`EDITOR`.
6. **Post-compose submit menu** for `pr create` (Submit / Submit as draft /
   Open in browser / Cancel), mirroring gh's "What's next?".
7. Replace the remaining `typer.prompt` calls with `questionary` for a
   consistent look.

### P3 — nice to have
8. **Multiselect reviewers** in interactive `pr create`
   (`questionary.checkbox` over workspace members).
9. **Relative timestamps** ("about 2 hours ago") in list/view output.
10. **Pager** for long output (`pr diff`, `pipeline logs`, `view`) via
    `click.echo_via_pager`, honoring `BJ_PAGER`/`PAGER`.
11. Global `--no-input` and a `BJ_PROMPT_DISABLED` analog.

## Already fixed
- `auth login` free-text auth-mode entry → arrow-key select + masked token.
- Confusing "Default workspace" login prompt removed (login = credentials only).
