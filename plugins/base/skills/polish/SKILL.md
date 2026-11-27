---
name: polish
description: "Polishes the current diff without changing behavior: deletes needless comments the diff added, then removes AI cruft, dead code, duplication, and needless abstractions, never editing outside it. Use after writing a non-trivial change, when a change feels bloated, or when asked to polish, clean up, deslop, or simplify; also a step of gbase:go and gbase:monitor."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent
---

# /gbase:polish

A comment pass, then two behavior-preserving passes over the current diff. No bug fixes, contract changes, or API tweaks — if you find a real bug, report it instead of patching it. The one exception is Pass 0 under `risk: medium` or `high`, which may replace a workaround with its root-cause fix.

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. 세부: [output-language.md](../../references/output-language.md).

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking.

## Posture — split by risk

- **Reusing existing code, removing literal duplicates, deleting dead code** — low risk, high value: be aggressive. Leave such a finding only after grepping and confirming there is no existing helper or other copy.
- **New abstractions** (wrappers, config arrays, data-driven lists, indirection) — high risk: be conservative. If sibling files solve the same shape explicitly, match them; three similar lines beat a premature abstraction.

A repo culture of "explicit over clever" argues against new cleverness, not against calling a utility that already exists.

## Scope

Uncommitted changes if any; otherwise the latest commit; explicit paths from the caller win. Every changed file goes through every lens — a file left out must fall under a skip category and be named in the report.

Skip entirely: pure renames/moves, dependency bumps, generated code, reverts, intentionally instrumented debug diffs, and anything the user called a prototype or "ship as-is".

## Pass 0 — comments

Run `"${CLAUDE_SKILL_DIR}/scripts/added-comments"` on the scope (no argument: uncommitted changes and untracked files; paths from the caller: `-- <paths>`, the same for those paths; a commit scope: its `git diff` arguments, e.g. `HEAD~1 HEAD`) and do what its `next:` line says.

- `next: skip` → launch no agent for comments; the report line is `Comments: skip — no comments on added lines`.
- `next: read the diff yourself` (git failed) → decide the same thing by reading the changed lines.
- `next: comment pass` → `Read` [references/comments.md](references/comments.md) and finish it before Pass 1. It runs pstack's `no-comments` (one comment-only agent judges every comment on the added lines), scaled by the `risk:` the caller passed.

## Pass 1 — three lenses in parallel

Spawn three `general-purpose` sub-agents at once with `model: "sonnet"` (they only propose — the resolution step below is the gate; a model the user names wins), each given the full diff and one lens. They return proposals (`file, line_range, before, after, rationale`) and edit nothing.

- **A — AI cruft & dead code:** (comments are Pass 0's; a lens proposes no comment edit) defensive checks on trusted paths, `any`/`ignore` casts hiding type errors, handling for impossible cases, leftover scaffolding, compat shims with no callers.
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
Comments: skip — <reason> | audited N, deleted D, kept K, fixed F, open O (+ one row per `fixed` and `open` item, as comments.md writes them)
Pass 1 — Lens A/B/C: proposed N, filtered Y, applied Z (each)
Pass 2 — applied: …; awaiting confirm: … (⚠ out-of-diff)
Rejected: <proposal — why>
Excluded: <file — skip reason> | none
Verification: <command> → pass | fail (reverted: <file>)
```
