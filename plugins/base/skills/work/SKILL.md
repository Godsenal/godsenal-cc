---
name: work
description: "The default way to carry out a task in gbase: picks one route, reads that route's playbook only then, and works it with gbase's scout/worker subagents. Use before starting a task that touches more than one file or changes a signature other files call, involves a design or architecture choice, is a bug whose cause is not yet known, a performance issue, or a diagnosis from a trace or profile, or spans several PRs; also on /gbase:work <task>. Not for a quick question, a one-line edit, or a contained change to one file with an obvious check. A finished code change continues into gbase:go (review, verify, PR) — asked first unless the user typed /gbase:work for it or asked to ship it."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Skill
---

# /gbase:work

Pick a route, read its steps, hand the result to `go`. This is pstack's `poteto-mode` (MIT) inside gbase. It keeps applying after the first task.

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. 세부: [output-language.md](../../references/output-language.md).

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking.

## 0. Before the route

- Unpushed `gbase:pause` commits on this branch (`wip:` subject, `Intent:` body) → `gbase:pickup` first, then route what's left.
- No `<!-- gbase:verify:start -->` block in `CLAUDE.md`/`AGENTS.md` → say once that `/gbase:setup` adds one.
- Behind the upstream → fast-forward first.
- **A ticket reference** in the request or the branch name (`ABC-123`, `#123`, a tracker URL) and `git config --get gbase.conventions` prints a path → read [environment.md](../../references/environment.md) before the route.
- **Skills the repo names** in `CLAUDE.md`/`AGENTS.md` for this kind of work are loaded before the first edit, as todo items. After that, load only what the todo list or this file names.
- **The task touches what a user sees** — a screen, component, on-screen copy, onboarding, an empty/loading/completion state, an icon, a store screenshot. Judge by the files it will touch (`.tsx`, `.swift`, styles, views), not by its wording. First check the two skips, and when one applies do not call the skill at all:
  - the task hands over a design to match (a Figma file or link, a mockup the user picked) → `skip: design given`. Build to that design.
  - only logic changes inside a UI file (a handler, a data fetch) → `skip: no visible change`.
  - Otherwise → `Skill(skill: "gbase:design-taste")` before the first edit, as a todo item.
- **More than one PR's worth** — two or more changes that could each ship and be reviewed on their own (separate features, a migration plus the feature that uses it, unrelated screens) → split before the first edit, without asking. Do only the first slice, the one the others depend on, through Ship, and report every other slice as its own `남은 작업: <task>` line at column 0 that a fresh run can take with no other context. Work that only holds together as one change (one screen's design pass, a rename across its callers) is done whole, with the reason in one line.

## 1. Pick one route

A file name below is a playbook in `../poteto-mode/playbooks/`. Once its row is picked, not before, `Read` [references/playbooks.md](references/playbooks.md) and the playbook, and put its numbered steps into the todo list verbatim, ahead of task-specific items. A skipped step stays as `skip: <reason>`.

| The task is | Its steps |
|---|---|
| A contained change: one file or one obvious edit, with an obvious check | Nothing to read. Make it, check it on the real artifact, then Ship. |
| An idea, open product choices, "기획해 줘" | `gbase:plan`. It ends in a plan file and slices; each slice is its own task here. |
| A read-only question (how, why, A or B) | `gbase:how`, plus `gbase:why` for history. Answer with evidence or a tradeoffs table. No code. |
| A defect to fix | `gbase:bug-fix`, then Ship |
| New or changed behavior | `feature.md` |
| Structure changes, behavior doesn't | `refactoring.md` |
| A measured slowness | `perf-issue.md` |
| A capture to diagnose: a CPU profile, trace, heap snapshot, spindump | `trace-forensics.md` |
| A live process that spins, leaks, or glitches, no capture yet | `runtime-forensics.md` |
| One metric pushed to a target over many tries; a port that must look identical; a blind comparison of skills or prompts | `hillclimb.md`; `visual-parity.md`; `eval.md` |
| A decision to make cheaply (which layout, which approach) | `prototype.md`. It doesn't ship. |
| "Until X passes", "keep going", unattended | `autonomous-run.md` |
| Phased work spread over several PRs | `multi-phase-plan.md` for the plan file. A task that also asks for the first phase builds that PR by its own row; the rest are `남은 작업:` lines. |

No row fits → say so and plan the steps under the principles below. On any route, a number (a baseline, a speedup, a regression) starts at `../principle-explain-the-number/SKILL.md` and is reported only after the seven questions of [benchmark-checklist](../benchmark-checklist/SKILL.md).

## 2. Ship

A route that changed files ends with `Skill(skill: "gbase:go")`: polish, review, verify, PR, monitor, scaled by risk. An answer, a diagnosis, a plan file, or a prototype doesn't ship.

**Nothing ships by hand.** No `git commit`, `git push`, `gh pr create`, or `gh pr merge` of your own, however small: a version bump, a one-line chore, a conflict fix, or a follow-up on a branch that already has a PR all go through `go`. In one week 9 of 51 PR runs shipped by hand and left no review, evidence, or settle record.

Before calling it, write the route's surface verification as `behavior:` lines (`behavior: <feature> → pass (<evidence>)`, or `behavior: skip — <reason>` when the surface can't be reached); `go` reuses them.

**Ship gate.** `go` pushes and opens a PR. Skip the question only when, for this task, the user typed `/gbase:work <task>` or explicitly asked to ship it or open a PR; an earlier task's request doesn't carry over, and "finish" or "wrap up" is not a ship request. Otherwise ask once before calling `go`: run it now, or stop with the change verified and uncommitted.

Add `--merge` only when the user asked for merging (this session) or the project's instructions say to merge PRs (its `CLAUDE.md`/`AGENTS.md`, or your memory for this project); otherwise stop at a merge-ready PR and say so. `go`'s own gates still apply, and a merge that would deploy (push-to-main OTA, production deploy) stops for confirmation.

## Principles

Most are pstack leaves, `../principle-*/SKILL.md`. Read one when a call hinges on it; a contained change needs none.

- **Prove it works.** Check the real artifact before calling it done: run it, read the actual value. "It compiles" and a sub-agent's "done" are not proof.
- **Smallest change that solves it.** Delete before adding; no speculative guards, options, or abstractions.
- **Fix root causes.** Fix the first place the system went wrong, not where it surfaced; a guard is a fix only when the state it handles is legitimate.
- **Root cause before smallest.** When those two disagree, the root-cause fix wins and "smallest" only picks among changes that fix it: a guard, retry, or shorter cache time over a state that should never exist solves nothing, a fix bigger than one PR ships its first slice with the rest as `남은 작업:` lines, and a stopgap the task itself prescribes ships with the root-cause fix on a `남은 작업:` line.
- **A correction becomes a check, not another line.** When the task corrects a mistake an agent made (the user says it happened again, or hands over `교훈:` lines), read [references/correction.md](references/correction.md) before the fix.
- **Verify in small units**, each checked before the next. **Model the domain**: a state machine, typed model, or table, not the same conditionals across files. **Test behavior, not implementation.**
- **Don't block on reversible work.** Do it and report it. Stop only for irreversible actions — deploys (including a merge that triggers one), store submits, data deletion, force-push to shared branches, messages to people — and for product calls no experiment can settle. If running something can answer the question, run it.

## Subagents

Sweeping many files, long logs, CI output, transcripts, or a large capture goes to `subagent_type: "gbase:scout"`. Two or more independent code units go to one `subagent_type: "gbase:worker"` each, launched together; a single unit, a design call, or units that write the same files stay here. Read [references/workers.md](references/workers.md) before launching either, and read what comes back yourself.

## Reply

- Lead with what changed for whoever uses the result, then what the next maintainer inherits.
- Each claim carries its evidence or a label in the same sentence — 확인함 (ran or read it), 추정 (inferred), 미확인. Never hand the user a check you could run.
- Link only what you produced or read this session; a PR as its full URL.
- Write plainly as you draft: short declarative sentences, no dash or colon as a connector, no filler, stacked hedges, or 번역투 ("~에 대해", "~을 통해"). A doc you wrote gets the full pass from an `Agent` told to run `Skill(skill: "gbase:unslop")` on the file.
- Asked whether to do something, give your real judgment; "this doesn't earn its place" is a valid answer.
