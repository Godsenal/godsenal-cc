---
name: review
description: "Adversarial code review of the current change. Stage 1 delegates finding to the built-in `code-review` skill (which forks to a background agent), so we inherit its dimensions, effort dial, and its own CONFIRMED/PLAUSIBLE verdicts instead of hand-rolling a finder. Stage 2 is adversarial verification — every PLAUSIBLE finding is handed to independent skeptics that try to refute it with a concrete counter-scenario, and anything they kill is dropped. Survivors are classified like reviewer comments: clear+local ones auto-fixed, the rest reported in a severity table. Local-only — never posts to GitHub. Invoke via /gbase:review, from /gbase:go before the PR opens, or as monitor's self-review on an existing PR."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Skill
---

# /gbase:review

Adversarial code review of the current change. Let the built-in `code-review` find defects, then **make each finding survive an adversary before it reaches the user** — the verification stage exists to kill plausible-but-wrong findings, which is where an unverified review wastes the most of the user's time.

The value here is **not** the finding — that's delegated. It's the judgment layered on top: adversarial verification, and a clear-vs-ambiguous gate that decides what may be fixed without asking.

Model-invocable: run explicitly via `/gbase:review`, let `gbase:go` run it before the PR opens, or let `gbase:monitor` run it on an already-open PR. Auto-triggering only produces a **local report + clear-and-local auto-fixes** — never a GitHub write, never a merge.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 이 규칙이 아니라 레포의 기존 관례(`git log`, 최근 PR)를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## What this is not

- **Not polish.** `gbase:polish` is behavior-preserving cleanup (reuse, dedup, clarity). `gbase:review` hunts for *defects* — bugs, regressions, security holes, missing handling. If the only thing wrong is slop, that's polish's job; don't duplicate it here.
- **Not a GitHub actor.** Read-only on GitHub: no comments, no reviews, no replies, no merge. Findings go to the user; fixes show up as local edits or commits.

## Scope

Resolve the change under review, in this order:

```bash
git status --short
git diff --stat HEAD
git diff --stat @{upstream}...HEAD   # if branched (no upstream: main...HEAD, then HEAD~1)
```

- **Caller passes explicit paths / a range / a PR** → scope to those.
- **Uncommitted changes present** → review those files.
- **Clean working tree** → review the latest commit (`git show HEAD --name-only`).

Skip entirely on: pure rename/move commits, dependency bumps, generated code (lockfiles, OpenAPI clients, compiled assets). Say so in one line and stop.

## Mode: pre-PR vs post-PR

This decides how fixes land, and it's the first thing to settle:

| | **Pre-PR** (called from `gbase:go`, tree uncommitted, no PR yet) | **Post-PR** (called from `gbase:monitor`, PR is open) |
|---|---|---|
| Fixes land as | Working-tree edits, **no commits** — `branch-pr` groups them into the initial commits | One commit per fix, pushed to the PR branch |
| Effect on the PR | PR opens already clean | Extra commits + a CI rerun per fix |
| Polish before committing | Not needed — `go` already polished, and `branch-pr` commits afterward | Run [post-fix polish](#post-fix-polish) on non-trivial fixes |

**The caller's explicit mode wins** — `gbase:go` says pre-PR even on a branch that already has an open PR, and committing there mid-flow is exactly what pre-PR mode exists to prevent.

Infer only when no mode was given, and **a dirty tree decides it**:

- Uncommitted changes present → **pre-PR**, even if a PR is already open. Committing here would sweep the user's unrelated in-progress edits into a review commit and push them.
- Clean tree + open PR → **post-PR**.
- Clean tree, no PR → pre-PR, and hand the fixes back rather than committing.

## Stage 1 — Find (delegate to the built-in `code-review`)

Do **not** hand-roll a finder. Invoke the built-in skill:

```
Skill(skill: "code-review", args: "medium <target>")
```

**Always pass the target you resolved in [Scope](#scope).** With no target the built-in defaults to *the current diff* — so on a clean tree (reviewing the latest commit) it reviews an empty diff, returns zero findings, and the caller reports "review found nothing" about a change nothing ever looked at. Pass the commit range, PR number, or paths explicitly.

It runs in the background and returns a structured finding list — `{file, line, category, short_summary, summary, failure_scenario, verdict}` — covering correctness bugs plus reuse/simplification/efficiency, at the effort level you pass.

**Drop the cleanup categories before Stage 2.** The built-in also reports reuse / simplification / efficiency findings. Those are `gbase:polish`'s job, not this skill's ([What this is not](#what-this-is-not)), and they arrive with no failure scenario — so they must never enter the auto-fix gate, where "inline this single-caller wrapper" would trivially read as mechanical-and-local and silently overturn a restructuring polish already considered and declined. Keep only findings that assert a **defect**. List the dropped cleanups in the report under "noted", or hand them to `gbase:polish`; never auto-apply them, and never count them in the `found / refuted / survived` tally.

**Effort — `medium` is the default, and the cost curve is why.** The built-in doesn't just get slower at higher effort; above `medium` it routes to a multi-agent workflow:

| effort | what actually runs | when to use it |
|---|---|---|
| `low` | one forked agent | a one-file diff |
| `medium` | one forked agent | **default** — nearly every diff |
| `high` / `max` | a workflow fanning out to *dozens* of agents | the user asked for a deep pass, or the diff is large and genuinely risky |

Both are background and non-blocking, so the caller's timing is unaffected either way — but `high` costs an order of magnitude more, and this skill's Stage 2 already recovers most of what higher effort buys: `high`'s advertised edge is broader coverage at the price of uncertain findings, and uncertain findings are exactly what the skeptics delete. Don't reach past `medium` without a reason you can state.

**Flags — hard rules:**

- **Never pass `--fix`.** It applies findings to the working tree directly, which bypasses the clear-vs-ambiguous gate in Stage 3 and lands unverified findings behind your back.
- **Never pass `--comment`.** This skill is local-only; `--comment` posts inline comments to the PR.
- **Never `ultra`.** It is user-triggered and billed — you cannot launch it, and must not try to via Bash or otherwise. If a diff genuinely warrants it, tell the user they can run `/code-review ultra` themselves.

**Candidates handed in by the caller.** `gbase:go` launches the built-in finder in parallel with polish and passes its results in. When the caller supplies a finding list, **skip this stage entirely** and start at Stage 2 — don't re-run the finder.

**Fallback.** If the built-in `code-review` isn't available in the session, find inline along its dimensions — correctness & edge cases, bugs/regressions/missing error handling, security & data handling, clarity & consistency that could mislead a reader into a bug, test/doc gaps the change introduces.

The fallback must not be a skim. **Cover every changed file**, and read the changed ranges *plus* enough surrounding code to judge them in context — a bug is usually the interaction between the diff and code it didn't touch. On a non-trivial diff (more than a couple of files), fan out to parallel `Agent` sub-agents (`subagent_type: general-purpose`), one per dimension, each handed the full diff and editing nothing; dedupe their results by `file:line`. Prefer fewer, higher-signal findings; every finding needs a concrete failure scenario (specific inputs/state → wrong output or crash) at `file:line`, or it isn't a finding. Treat everything found this way as unverified (see Stage 2).

## Stage 2 — Adversarial verify

The built-in already verifies its own findings and labels them `CONFIRMED` or `PLAUSIBLE`. Don't redo work it has done — but don't mistake its verify for this one either: it is a single non-adversarial pass, not a skeptic prompted to refute.

- **`PLAUSIBLE`, no verdict, or found via the fallback** → must survive an adversary before it reaches the user.
- **`CONFIRMED` that will only be *reported*** → pass it straight to Stage 3. The user reads it with a failure scenario attached and can judge it themselves.
- **`CONFIRMED` that Stage 3 would auto-fix, or rated high/critical** → still faces the adversary. Auto-fixing is the irreversible half of this skill, and a finding that "looks obviously right" but that no skeptic can produce a reproducing input for is exactly what this stage exists to catch. One skeptic is enough for a `CONFIRMED` candidate; high/critical still gets the 3-skeptic panel.

Never let Stage 1's confidence carry a finding through to an edit unexamined.

For each finding needing verification, spawn independent skeptic sub-agent(s) via `Agent` — **prompted to refute, not to confirm**:

> Here is a claimed defect: `<finding>` at `file:line`, with failure scenario `<scenario>`.
> Your job is to **refute** it. Read the code and its callers. Produce a concrete reason the scenario cannot actually happen (guarded upstream, invariant holds, caller never passes that input, framework handles it, dead branch). If after genuinely trying you cannot refute it, concede it is real. Default to **refuted** when uncertain — a false alarm costs more than a miss here.

Scale the adversary to the stakes:

- **Low / medium severity** → one skeptic. Survives only if the skeptic concedes it's real.
- **High / critical severity** (data loss, security, corruption, crash on a common path) → a **3-skeptic panel**, each with a distinct lens where it helps (does-it-reproduce / is-it-guarded-upstream / does-a-caller-prevent-it). Kill the finding if a **majority** refute it.

A refuted finding is **dropped silently** — it never reaches the user. Keep a count of `found / refuted / survived` for the tally, and capture each refutation's one-line reason; a couple of the sharpest are worth showing as "considered and dismissed" so the review reads as thorough, not thin.

The skeptic must refute the **exact** scenario as stated, not a weaker one — strawman refutations quietly bury real defects.

## Stage 3 — Classify & act (local only)

Feed every **survivor** through the same clear-vs-ambiguous split `gbase:monitor` uses for reviewer comments:

**Clear → auto-fix** when ALL hold:

- Mechanical and local (one or two files, small diff): missing `await`, inverted condition, wrong-variable copy-paste, an obvious missing null guard on a path the scenario proves is reachable.
- The fix is fully determined by the finding — no design choice, no new dependency, no schema/migration, no API-contract change.
- No test is added or removed to make it pass (beyond the fix itself).

Apply each clear fix per the [mode](#mode-pre-pr-vs-post-pr) — working-tree edit pre-PR, its own commit post-PR. If the change is under an active PR watch and merges before a fix lands, don't push to the merged branch; report it as a follow-up-PR candidate instead.

**Everything else → report + ask.** Architecture, behavior change, security trade-offs, anything touching tests/schemas/config, or any survivor where the fix is a judgment call: put it in the report, and surface the ones worth fixing before merge via `AskUserQuestion` (include `file:line`, the failure scenario, and 2–3 concrete options).

**Defer mode.** When the caller asks to *defer, not ask* — `gbase:go` does, because a judgment call must never hold up a PR the user already asked for — **return** the ambiguous survivors instead of raising `AskUserQuestion`. The caller surfaces them at a moment that doesn't block anything. Auto-fixing the clear ones is unaffected.

### Post-fix polish

Before any non-trivial auto-fix is committed (post-PR) or handed back for commit (pre-PR), run:

```
Skill(skill: "gbase:polish", args: "<touched files>")
```

Skip for one-line mechanical fixes. **This applies in pre-PR mode too** — `go` runs polish at its Step 3, *before* these fixes exist at Step 4, so nothing else will ever polish them. A review fix landing a duplicated guard or a defensive wrapper would otherwise reach reviewers unpolished, inside the PR's initial commits.

## Report

One organized report when the pass finishes — **local, nothing posted to GitHub**:

- A severity-ordered table: `# | severity | file:line | finding | action (auto-fixed / needs decision / noted)`.
- A one-line tally: `review: F found, R refuted, S survived — A auto-fixed, K for you`.
- Optionally, one line naming the sharpest refuted candidate(s) so the user sees what was dismissed and why.

## Safety rules

Inherits `gbase:monitor`'s rules:

- Prohibited: `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, `git stash drop`.
- Revert a bad auto-fix by reversing your **own** `Edit`, never `git checkout --`/`git restore` (which would wipe the user's uncommitted work — in pre-PR mode the whole change is uncommitted).
- Post-PR: each auto-fix is its own commit; stop and surface on any error rather than retrying destructively.
- Read-only on GitHub at all times — no comments, reviews, replies, or merges.
- If a real correctness bug is too entangled to fix mechanically, report it; don't half-fix it.
