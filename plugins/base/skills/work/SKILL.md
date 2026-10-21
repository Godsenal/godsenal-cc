---
name: work
description: "How to carry out a non-trivial task — classifies the request (investigation, bug, feature, refactor, perf, prototype, or run-until-done), copies that route's steps into the todo list, and works them under a few core principles with gbase's scout/worker subagents. Use before starting a task that touches more than one file or changes a signature other files call, involves a design or architecture choice, or is a bug whose cause is not yet known or a performance issue; also on /gbase:work <task>. Not for a quick question, a one-line edit, or a contained change to one file with an obvious check. A finished code change continues into gbase:go (review, verify, PR) — asked first unless the user typed /gbase:work for it or asked to ship it."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Skill
---

# /gbase:work

Start a task here. It picks a route, follows it, and hands the result to `go`. Modeled on pstack's `poteto-mode` (MIT) without its personal style: the routes come from its playbooks, the principles from its principle skills. The body stays in context for the session, so it keeps applying after the first task.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking.

## 0. Before the route

- Unpushed `gbase:pause` commits on this branch (`wip:` subject, `Intent:` body) → `gbase:pickup` first, then pick the route for what's left.
- No `<!-- gbase:verify:start -->` block in `CLAUDE.md`/`AGENTS.md` → say once that `/gbase:setup` would make the verify step reliable, then continue.
- Behind the upstream → fast-forward before starting.

## 1. Pick one route and copy its steps

Put the route's steps into the todo list verbatim, before task-specific items. A step you skip stays in the list as `skip: <reason>`. If none fits, say so and plan the steps yourself under the principles below.

**Investigation** — a read-only question (how does X work, why is Y, should we do A or B).
1. `gbase:how`; add `gbase:why` for motivation or history.
2. Answer with the evidence, or a recommendation with a tradeoffs table. No code, no PR — if it turns into a change, re-route.

**Bug** — a defect to fix: `gbase:bug-fix`, then **2. Ship** below.

**Feature** — new or changed behavior.
1. `gbase:how` over the area it touches.
2. Name the data shape before writing logic.
3. Split it into units, each with its own check. Independent units go to `gbase:worker`s launched together (see Subagents); dependent units are built here in order, each verified before the next.
4. Verify on the surface the user touches (the repo's verify skill, the CLI, the screen) — not only tests.

**Refactor** — structure changes, behavior doesn't.
1. Pin the current behavior first: a characterization test, snapshot, or before/after output diff. Type check and lint are not a pin.
2. Delete dead code and one-caller wrappers before adding the new shape.
3. Move in small steps, each keeping the pin green; migrate every caller and delete the old API in the same change.
4. Keep it only if it makes the code easier to follow; otherwise revert. A bug found on the way is split out, not fixed here.

**Perf** — a measured slowness.
1. Measure a baseline first; don't reason from source instead of measuring.
2. Try the cheapest fix first: don't do it → don't do it again → do less → do it later → do it concurrently → do it cheaper. Stop at the first that meets the target.
3. Measure again and report baseline → after with units.

**Prototype** — a decision to make cheaply (which layout, which approach).
1. Name the decision. No decision, no prototype.
2. Build throwaway variants in a scratch dir outside the source tree, behind one switcher when comparing.
3. Observe each (screenshot, output, timing), recommend one, and hand it to Feature. The prototype doesn't ship.

**Run until done** — "until X passes", "keep going".
1. Write the exit condition as a checkable predicate before the first iteration.
2. Each iteration makes the smallest change the evidence justifies, checks the predicate, keeps it if it advanced, reverts it if not.
3. A plateau isn't a stop — change approach. Never relax the predicate to declare victory; surface a real dead end instead.

## 2. Ship

Every route except Investigation and Prototype ends with `Skill(skill: "gbase:go")` — review ∥ polish, verify, PR, monitor.

**Ship gate.** `go` pushes and opens a PR. Skip the question only when, for this task, the user typed `/gbase:work <task>` or explicitly asked to ship it or open a PR; an earlier task's request doesn't carry over, and "finish" or "wrap up" is not a ship request. Otherwise ask once before calling `go`: run it now, or stop with the change verified and uncommitted (the user runs `/gbase:go` later). The rest of the route needs no confirmation.

Add `--merge` only when the user asked for merging (this session) or the project's instructions say to merge PRs (its `CLAUDE.md`/`AGENTS.md`, or your memory for this project); otherwise stop at a merge-ready PR and say so. The default is not to merge — on a shared repo a merge is someone else's call. `go`'s own gates still apply, and a merge that would deploy (push-to-main OTA, production deploy) stops for confirmation.

## Principles

- **Prove it works.** Check the real artifact before calling it done — run it, read the actual value. "It compiles" and a sub-agent's "done" are not proof.
- **Verify in small units.** In multi-step work, check each unit before starting the next; a break caught where it happened is cheap.
- **Smallest change that solves it.** Delete before adding; no speculative guards, options, or abstractions.
- **Fix root causes.** Fix the first place the system went wrong, not where it surfaced; a guard is a fix only when the state it handles is legitimate.
- **Model the domain.** Stateful or heavily branching logic gets a structure — a state machine, typed model, or table — instead of the same conditionals repeated across files.
- **Test behavior, not implementation.** A test should fail when the behavior breaks and keep passing when only internals change.
- **Explain the number.** Before trusting a measurement, name what limited it and rule out that it measured something else (errors, cached or skipped work, noise).
- **Don't block on reversible work.** Do it and report it. Stop only for irreversible actions — deploys (including a merge that triggers one), store submits, data deletion, force-push to shared branches, messages to people — and for product calls no experiment can settle. If running something can answer the question, run it instead of asking.

## Subagents

- **Bulk goes out, conclusions come back.** Exploring many files, reading long logs, CI output or transcripts, and independent investigations go to `subagent_type: "gbase:scout"` (Sonnet, no edit tools), several in one message when independent; keep only their summaries here.
- **Two or more independent code units → one `subagent_type: "gbase:worker"` per unit, launched together** (one message, `run_in_background: true`, `isolation: "worktree"`). Brief each with the unit, its check, and file pointers, not pasted context. Workers see only committed `HEAD`, not your uncommitted edits: paste any shared shape they depend on into each brief, and keep units off files you've changed.
  - Independent means neither needs the other's result and they don't write the same files. A single unit, a design call, or units that write the same files stay here, in sequence.
  - When they're back, take each change as a patch, without commits (no hooks to fail): `git -C <wt> add -A && git -C <wt> diff --cached --binary | git apply`. Read it, run the checks once on the whole, then clean up with `git worktree remove --force <wt> && git branch -D <its branch>`.
  - Skills that dispatch their own agents (`review`, `polish`, `how`, `why`) keep their types.
- **Fresh agent per new task**, briefed with the original ask, every later instruction, and the previous agent's report. Continue an existing agent only when the work needs state that lives in it (its checkout, a running simulator or server).
- **You own their output.** Read the diff yourself and write your own summary; never relay "done" unchecked.
- **A second opinion is the same prompt on another model** — agreement is the signal, not a persona.

## Reply

- Lead with what changed for whoever uses the result, then what the next maintainer inherits.
- Each claim carries its evidence or a label in the same sentence — 확인함 (ran or read it), 추정 (inferred), 미확인. Never hand the user a check you could run.
- Link only what you produced or read this session; a PR as its full URL.
- Load `gbase:unslop` once before your first user-facing draft and write replies and docs by its rules as you draft, not as a cleanup pass; PR text already goes through it in `branch-pr`.
- Asked whether to do something, give your real judgment; "this doesn't earn its place" is a valid answer.
