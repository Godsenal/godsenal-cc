# Flow baseline

The numbers a weekly check compares against: how much instruction text a PR run loads, and how long and how much a run takes. No skill links this file. Re-measure with `python3 scripts/read-budget.py` (routes), `--skills` (bodies), and `--log <run>/log.jsonl …` (what real runs loaded).

## What a PR run's main session loads (characters)

| route | 2026-11-17 before (1.54.0) | after 1.55.0 | target |
|---|---|---|---|
| `low` — work, go, branch-pr, monitor, polish, unslop | 72,638 | 47,564 | 25,000 |
| `medium` — low + review, compat-check, branch-pr's `pr-body.md` | 87,678 | 68,256 | 40,000 |
| `high` — same files as medium today | 87,678 | 68,256 | measured only |
| `+headless` — monitor's `settle.md` and `merge.md`, review on `low` | 7,569 | 13,663 | none set |
| `+ui` — design-taste | 6,527 | 6,527 | none set |

A headless `low` run that merges loads `low` + `+headless`: 80,207 before, 61,227 after. `scripts/read-budget.json` holds each route's file list and the limit `check.py` enforces; the limits are the "after" column rounded up, and come down as the routes shrink.

Real runs, for comparison: across 39 work runs of 2026-11-14 to 11-17 that reached a PR, the main session invoked `go` in 39, `branch-pr` 37, `unslop` 35, `monitor` 33, `polish` 30, `compat-check` 27, and `review` 19. It also pulled part of `references/orchestrator.md` in 28 (mostly the Evidence file section, about 3,900 characters, or Settle, about 2,300) and `headless.md` in 13 (4,500). None of those used the Read tool: sessions fetch a reference with `sed` or `cat` in Bash, so `--log` counts Bash reads too, at the whole file's size (an upper bound). Counted that way the median run loaded 67,262 characters (min 14,275, max 199,944).

## Skill bodies (characters)

| skill | 2026-10-18 | 2026-11-17 before | after 1.55.0 |
|---|---|---|---|
| work | 6,719 | 12,602 | 12,450 |
| go | 8,235 | 14,352 | 14,200 |
| branch-pr | 13,969 | 19,998 | 6,477 (+ `pr-body.md` 5,956, `local-mode.md` 1,356) |
| monitor | — | 15,836 | 4,739 (+ `settle.md` 4,030, `merge.md` 2,216, `comments.md` 3,137, `conflicts.md` 2,033) |
| review | — | 7,569 | 7,417 |
| compat-check | — | 7,471 | 7,319 |
| polish | — | 5,685 | 5,533 |
| unslop | — | 4,165 | 4,165 |

## Run medians (work runs that reached a PR)

| window | runs | wall-clock | cost | tool calls | after `go` |
|---|---|---|---|---|---|
| 2026-11-10 to 11-13 | part of 95 | 27 min | $6.4 | 96 | 30–40% of tool calls, 50% of main output tokens, 4 subagents (median) |
| 2026-11-14 to 11-17 | part of 95 | 15 min | $5.8 | 66 | same shares |

The smallest runs end in 2–5 minutes and $1–2, so the `low` route was already light in tool calls; what this baseline tracks is the text it loads and the share spent after `go`.

## `compat-check` calls

Of 126 November work runs with a PR and a log, 71 called `compat-check`. Two of those changed only docs, tests, and images; of the 12 whose verdict is in the log, 11 were `✅` and 1 `⚠️` (a CI and deploy-workflow change). A call costs the 7,400-character body and a median of 0 tool calls. `ship-prep` now skips it for docs (by extension), tests, and images-only changes; every change with a code or config file, or an always-high path, still gets it.

## Compare next

After a week of runs on 1.55.0: the median wall-clock, cost, tool calls, and the share after `go`, against the 11-14 to 11-17 row; and `read-budget.py --log` on those runs against the `low` + `+headless` figure (61,227), to see that the `references/` files are read when their branch comes up (`settle.md` in every headless run) and not otherwise. In four test sessions on 1.55.0, `settle.md`, `pr-body.md`, and `local-mode.md` were each read when their condition held, and `pr-body.md` was not read for a `low` change.
