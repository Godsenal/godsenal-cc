# Flow baseline

The numbers a weekly check compares against: how much instruction text a PR run loads, and how long and how much a run takes. No skill links this file. Re-measure with `python3 scripts/read-budget.py` (routes), `--skills` (bodies), and `--log <run>/log.jsonl …` (what real runs loaded).

## What a PR run's main session loads (characters)

| route | 2026-11-17 before (1.54.0) | after 1.55.0 | after 1.56.0 | target |
|---|---|---|---|---|
| `low` — work, go, branch-pr, monitor | 72,638 | 47,564 | 24,995 | 25,000 |
| `medium` — low + go's `review.md` and `verify.md`, branch-pr's `pr-body.md` | 87,678 | 68,256 | 37,228 | 40,000 |
| `high` — same files as medium today | 87,678 | 68,256 | 37,228 | measured only |
| `+headless` — go's `orchestrated.md` and `review.md`, monitor's `settle.md` and `merge.md` | 7,569 | 13,663 | 12,462 | none set |
| `+merge` — go's `draft-merge.md`, monitor's `merge.md` | — | — | 3,472 | none set |
| `+playbook` — work's `playbooks.md` and one playbook (`feature.md`, 2,800; the others are 831 to 4,466) | — | — | 5,763 | none set |
| `+ui` — design-taste | 6,527 | 6,527 | 6,527 | none set |

A headless `low` run that merges loads `low` + `+headless`: 80,207 before, 61,227 on 1.55.0, 37,457 on 1.56.0. `scripts/read-budget.json` holds each route's file list and the limit `check.py` enforces. On 1.56.0 the `low` and `medium` limits sit at their targets (a limit can't go below its target).

Three things moved in 1.56.0. The numbers before 1.56.0 count the files each route listed then, so the `low` and `medium` rows are not the same file list across columns; the four bodies `low` lists now were 37,866 on 1.55.0:

- `polish`, `unslop` (low) and `review`, `compat-check` (medium) left the main session: `go`, `branch-pr`, and `monitor` launch an `Agent` told to call the skill. That is 9,698 characters off `low` and 14,736 more off `medium`. A subagent starts with its own context (about 44,000 tokens for a trivial one, mostly cached), so this trades main-session text and the skill's working output for one agent launch per skill.
- `go` kept the steps every run takes (14,200 → 4,885) and split the rest into `references/`: `review.md` 2,606, `verify.md` 3,068, `draft-merge.md` 1,256, `orchestrated.md` 3,610.
- `work` dropped its own route steps for a route table (12,450 → 9,396) and reads the pstack playbook when a task takes that route, plus `references/playbooks.md` (2,963) and `references/correction.md` (767).

`read-budget.py` counts whole files. A skill invoked through the `Skill` tool arrives without its frontmatter (about 2,600 characters across the four `low` bodies), so the real `low` load is that much smaller; `--log` measures the text as it arrived.

Real runs, for comparison: across 39 work runs of 2026-11-14 to 11-17 that reached a PR, the main session invoked `go` in 39, `branch-pr` 37, `unslop` 35, `monitor` 33, `polish` 30, `compat-check` 27, and `review` 19. It also pulled part of `references/orchestrator.md` in 28 (mostly the Evidence file section, about 3,900 characters, or Settle, about 2,300) and `headless.md` in 13 (4,500). None of those used the Read tool: sessions fetch a reference with `sed` or `cat` in Bash, so `--log` counts Bash reads too, at the whole file's size (an upper bound). Counted that way the median run loaded 67,262 characters (min 14,275, max 199,944).

From 1.56.0 the main session no longer invokes `polish`, `review`, `compat-check`, or `unslop`, so `result.json`'s `skills` lists only `work`, `go`, `branch-pr`, and `monitor` for a normal run. Count the four it stopped invoking from `subagent_skills` (1.57.1 on; for an older run, the `Skill` calls in `log.jsonl` whose event has a `parent_tool_use_id`). The first two work runs on 1.56.0 (2026-11-17) each show `code-review`, `polish`, `review`, `compat-check`, and `unslop` there.

## Skill bodies (characters)

| skill | 2026-10-18 | 2026-11-17 before | after 1.55.0 | after 1.56.0 |
|---|---|---|---|---|
| work | 6,719 | 12,602 | 12,450 | 9,396 (+ `playbooks.md` 2,963, `correction.md` 767, `workers.md` 1,814) |
| go | 8,235 | 14,352 | 14,200 | 4,885 (+ `review.md` 2,606, `verify.md` 3,068, `draft-merge.md` 1,256, `orchestrated.md` 3,610) |
| branch-pr | 13,969 | 19,998 | 6,477 (+ `pr-body.md` 5,956, `local-mode.md` 1,356) | 6,227 (+ `pr-body.md` 6,559, `local-mode.md` 1,356) |
| monitor | — | 15,836 | 4,739 (+ `settle.md` 4,030, `merge.md` 2,216, `comments.md` 3,137, `conflicts.md` 2,033) | 4,487 (`comments.md` 3,592, `conflicts.md` 2,349) |
| review | — | 7,569 | 7,417 | 7,417, read by a subagent |
| compat-check | — | 7,471 | 7,319 | 7,319, read by a subagent |
| polish | — | 5,685 | 5,533 | 5,533, read by a subagent |
| unslop | — | 4,165 | 4,165 | 4,165, read by a subagent |

## Run medians (work runs that reached a PR)

| window | runs | wall-clock | cost | tool calls | after `go` |
|---|---|---|---|---|---|
| 2026-11-10 to 11-13 | part of 95 | 27 min | $6.4 | 96 | 30–40% of tool calls, 50% of main output tokens, 4 subagents (median) |
| 2026-11-14 to 11-17 | part of 95 | 15 min | $5.8 | 66 | same shares |

The smallest runs end in 2–5 minutes and $1–2, so the `low` route was already light in tool calls; what this baseline tracks is the text it loads and the share spent after `go`.

## `compat-check` calls

Of 126 November work runs with a PR and a log, 71 called `compat-check`. Two of those changed only docs, tests, and images; of the 12 whose verdict is in the log, 11 were `✅` and 1 `⚠️` (a CI and deploy-workflow change). A call costs the 7,400-character body and a median of 0 tool calls. `ship-prep` now skips it for docs (by extension), tests, and images-only changes; every change with a code or config file, or an always-high path, still gets it.

## Compare next

After a week of runs on 1.56.0: the median wall-clock, cost, tool calls, and the share after `go`, against the 11-14 to 11-17 row; and `read-budget.py --log` on those runs against the `low` + `+headless` figure (37,457), to see that the `references/` files are read when their branch comes up (`settle.md` and `orchestrated.md` in every headless run, `verify.md` on every `medium` change) and not otherwise. Watch three things the subagent move could cost: the number of `Agent` launches per run (polish, review, compat-check, and unslop are one each, and `subagent_skills` in `result.json` says which of them a run called), wall-clock, and whether review's fixes and polish's edits still land (the `review:` tally and polish's report in the final message).

Two test runs of `/gbase:go` on 1.56.0 (2026-11-17, a `medium` change in a scratch repo, headless with an orchestrator owner, Sonnet): both launched polish, the finder, review, compat-check, and unslop as agents, committed locally, and wrote the PR body draft, in 86 to 90 seconds and $1.09 to $1.12. The first skipped `verify.md` and wrote evidence lines in the wrong shape; `go` Step 4 and `orchestrated.md` were reworded, and the second read `verify.md`, ran the behavior check, and wrote four well-formed evidence lines. A third run skipped the unslop agent after `branch-pr`'s sentence about it had been softened; the sentence went back to an imperative, and a fourth run (101 seconds, $1.12) launched all five again. A fifth run, after `go` Step 1 got its `printenv` line back in prose, ran the check first and read `orchestrated.md`, but judged the finder's one low finding itself and launched no review agent (84 seconds, $0.78): one skip in five runs, to watch in real runs. No run pushed, so `monitor`'s self-review agent has not run end to end.

In four test sessions on 1.55.0, `settle.md`, `pr-body.md`, and `local-mode.md` were each read when their condition held, and `pr-body.md` was not read for a `low` change.
