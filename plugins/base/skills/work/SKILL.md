---
name: work
description: "The default way to carry out a task in gbase: picks one route and works it. Use before a feature, refactor, or fix that touches more than one file or changes a signature other files call, a design or architecture choice, a bug of unknown cause, a performance issue, a diagnosis from a trace or profile, or work that spans several PRs ('여러 파일에 걸쳐 구현해 줘', '리팩터링해 줘', '느린 이유 진단해 줘'). Not for a quick question, a one-line edit, a contained one-file change, or a change the request already spells out. A finished change continues into gbase:go, asked first unless the user asked to ship it."
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
- No `<!-- gbase:verify:start -->` block in `CLAUDE.md`/`AGENTS.md` → say once that `/gbase:setup` adds one. Behind the upstream → fast-forward first.
- **A ticket reference** in the request or the branch name (`ABC-123`, `#123`, a tracker URL) and `git config --get gbase.conventions` prints a path → read [environment.md](../../references/environment.md) before the route.
- **Skills the repo names** in `CLAUDE.md`/`AGENTS.md` for this kind of work → load them before the first edit, as todo items. After that, load only what the todo list or this file names.
- **The task corrects a mistake an agent made** (the user says it happened again, or hands over `교훈:` lines) → read [references/correction.md](references/correction.md) before the fix.
- **The task touches what a user sees** (a screen, component, on-screen copy, onboarding, an empty/loading/completion state, an icon, a store screenshot; judge by the files it will touch, `.tsx`, `.swift`, styles, views, not by its wording) → `Skill(skill: "gbase:design-taste")` before the first edit, as a todo item. Two skips don't call it at all: the task hands over a design to match (a Figma file or link, a mockup the user picked) → `skip: design given`, build to that design; only logic changes inside a UI file (a handler, a data fetch) → `skip: no visible change`.
- **More than one PR's worth** (changes that could each ship and be reviewed on their own: separate features, a migration plus the feature that uses it, unrelated screens) → split before the first edit, without asking. Do only the first slice, the one the others depend on, through Ship, and report every other slice as its own `남은 작업: <task>` line at column 0 that a fresh run can take with no other context. Work that only holds together as one change (one screen's design pass, a rename across its callers) is done whole, with the reason in one line.

## 1. Pick one route

| The task is | Its steps |
|---|---|
| A contained change: one file or one obvious edit, with an obvious check | Nothing to read. Make it, check it on the real artifact, then Ship. |
| An idea, open product choices, "기획해 줘" | `gbase:plan`; each slice its plan file ends with is its own task here. |
| A read-only question (how, why, A or B) | `gbase:how`, plus `gbase:why` for history. Answer with evidence or a tradeoffs table. No code. |
| A defect to fix | `gbase:bug-fix`, then Ship |
| Anything else: new or changed behavior, a refactor, a slowness, a capture or live process to diagnose, a metric to push, a port, an eval, a prototype, an unattended run, phased work | Now, not before, `Read` [references/playbooks.md](references/playbooks.md). Its table names the playbook in `../poteto-mode/playbooks/`; put that playbook's numbered steps into the todo list verbatim, ahead of task-specific items. A skipped step stays as `skip: <reason>`. |

On any route, a number (a baseline, a speedup, a regression) starts at `../principle-explain-the-number/SKILL.md` and is reported only after the seven questions of [benchmark-checklist](../benchmark-checklist/SKILL.md).

## 2. Ship

A route that changed files ends with `Skill(skill: "gbase:go")`: polish, review, verify, PR, monitor, scaled by risk. An answer, a diagnosis, a plan file, or a prototype doesn't ship.

**Nothing ships by hand.** No `git commit`, `git push`, `gh pr create`, or `gh pr merge` of your own, however small: a version bump, a one-line chore, a conflict fix, or a follow-up on a branch that already has a PR all go through `go`. In one week 9 of 51 PR runs shipped by hand and left no review, evidence, or settle record.

Before calling it, write the route's surface verification as `behavior:` lines (`behavior: <feature> → pass (<evidence>)`, or `behavior: skip — <reason>` when the surface can't be reached); `go` reuses them.

**Ship gate.** `go` pushes and opens a PR. Skip the question only when, for this task, the user typed `/gbase:work <task>` or explicitly asked to ship it or open a PR; an earlier task's request doesn't carry over, and "finish" or "wrap up" is not a ship request. Otherwise ask once before calling `go`: run it now, or stop with the change verified and uncommitted. Add `--merge` only when the user asked for merging (this session) or the project's instructions say to merge PRs (its `CLAUDE.md`/`AGENTS.md`, or your memory for this project); otherwise stop at a merge-ready PR and say so. `go`'s own gates still apply, and a merge that would deploy stops for confirmation.

## While working

- **Prove it works** on the real artifact: run it, read the actual value. "It compiles" and a sub-agent's "done" are not proof.
- A call that hinges on a principle (root cause or smallest change, a guard or a stopgap, how to split or verify, whether to stop and ask) → [references/principles.md](references/principles.md). A contained change needs none.
- Reading many files, long logs, CI output, transcripts, or a large capture → `subagent_type: "gbase:scout"`. Two or more independent code units → one `subagent_type: "gbase:worker"` each, launched together; a single unit, a design call, or units that write the same files stay here. Read [references/workers.md](references/workers.md) before launching either, and read what comes back yourself.

## Reply

Lead with what changed for its user, then what the next maintainer inherits. Each claim carries its evidence or a label in the same sentence (확인함, 추정, 미확인); never hand the user a check you could run. Link only what you produced or read this session, a PR as its full URL. Short declarative sentences, no filler, stacked hedges, or 번역투; a doc you wrote gets the full pass from an `Agent` told to run `Skill(skill: "gbase:unslop")` on the file. Asked whether to do something, give your real judgment.
