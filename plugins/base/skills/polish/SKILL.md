---
name: polish
description: "Polishes the current diff without changing behavior, in two passes — a three-lens cleanup (AI cruft & dead code, reuse & duplication, clarity & efficiency) run by parallel sub-agents, then a structural pass that collapses needless helpers and abstractions. Use after writing a non-trivial change, when a diff feels bloated, or when asked to polish / clean up / deslop / simplify. Also the polish step inside gbase:go and gbase:monitor. Unlike the built-in simplify, it is aggressive on reusing existing code but conservative on new abstractions, never auto-applies edits outside the diff, and reverts its own failed edits without touching the user's uncommitted work."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent
---

# /gbase:polish

Two behavior-preserving passes over the current diff. No bug fixes, contract changes, or API tweaks — if you find a real bug, report it instead of patching it.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 이 규칙이 아니라 레포의 기존 관례(`git log`, 최근 PR)를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Posture — split by risk

- **Reusing existing code, removing literal duplicates, deleting dead code** — low risk, high value: be aggressive. Leave such a finding only after grepping and confirming there is no existing helper or other copy.
- **New abstractions** (wrappers, config arrays, data-driven lists, indirection) — high risk: be conservative. If sibling files solve the same shape explicitly, match them; three similar lines beat a premature abstraction.

A repo culture of "explicit over clever" argues against new cleverness, not against calling a utility that already exists.

## Scope

Uncommitted changes if any; otherwise the latest commit; explicit paths from the caller win. Every changed file goes through every lens — a file left out must fall under a skip category and be named in the report.

Skip entirely: pure renames/moves, dependency bumps, generated code, reverts, intentionally instrumented debug diffs, and anything the user called a prototype or "ship as-is".

## Pass 1 — three lenses in parallel

Spawn three `general-purpose` sub-agents at once with `model: "sonnet"` (they only propose — the resolution step below is the gate; a model the user names wins), each given the full diff and one lens. They return proposals (`file, line_range, before, after, rationale`) and edit nothing.

- **A — AI cruft & dead code:** comments that narrate the code or the task, defensive checks on trusted paths, `any`/`ignore` casts hiding type errors, handling for impossible cases, leftover scaffolding, compat shims with no callers.
- **B — reuse & duplication:** unused imports/declarations, single-use variables, near-duplicate blocks (grep the repo and count every copy before proposing), logic that already exists in shared utils/hooks (search by behavior keyword, not just name), repeated literals, repeated computation.
- **C — clarity & efficiency:** deep nesting, convoluted conditionals, stale names, hot-path waste (work in loops, sequential `await` that could be `Promise.all`), avoidable re-renders (unstable inline props/callbacks into memoized components or list rows, unstable list keys), closures that keep large scopes alive.

Then resolve in the main agent:

1. Dedupe overlapping proposals.
2. Drop proposals that change observable behavior, are false positives on a closer read, or add a new abstraction that fights the local pattern. When rejecting, refute the proposal as stated, not a broader version of it.
3. Apply in-diff edits directly. A fix that needs files outside the diff is proposed, not applied — list the affected files and let the user confirm.
4. Before calling the pass clean, confirm the searches actually happened: every file seen by every lens, shared utils grepped, every duplicate's copies counted.

## Pass 2 — structural

One agent on the session's model (omit `model` — this is the judgment pass), whole-diff view, after Pass 1 lands. Look for restructurings that keep behavior and make the code simpler: helpers or layers the surrounding code makes unnecessary, one-caller wrappers and one-value parameters, conditional growth that wants a data structure, files that should split by responsibility, fixes applied at the wrong altitude (special cases stacked on shared infrastructure instead of fixing the mechanism).

Apply small contained edits directly. Anything that moves files, renames public APIs, or rewrites more than ~50 lines goes through `AskUserQuestion` with a one-line rationale first. Leave a restructuring that is only correct under an invariant the code doesn't enforce.

## Verification

After each pass, run the lightest check the project has for the touched files (`tsc --noEmit`, the configured linter, a focused test). Don't invent a check, and don't run native builds (`xcodebuild`, Gradle) — leave those to CI.

If a check fails, revert the offending edit by applying its `after → before` with `Edit`. Never `git checkout --` / `git restore`: polish edits on top of the user's uncommitted work, and those commands would wipe it.

## Report

```
Pass 1 — Lens A/B/C: proposed N, filtered Y, applied Z (each)
Pass 2 — applied: …; awaiting confirm: … (⚠ out-of-diff)
Rejected: <proposal — why>
Excluded: <file — skip reason> | none
Verification: <command> → pass | fail (reverted: <file>)
```
