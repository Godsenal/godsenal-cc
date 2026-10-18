---
name: review
description: "Adversarially reviews the current change for defects — bugs, regressions, security holes, missing handling. Delegates finding to the built-in code-review, has independent skeptic sub-agents try to refute each finding, auto-fixes the clear and local survivors, and reports the rest. Local-only; never posts to GitHub. Use when asked to review a change or find bugs before shipping; also runs inside gbase:go (before the PR) and gbase:monitor (on an open PR)."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Skill
---

# /gbase:review

Finding is delegated to the built-in `code-review`. This skill adds the judgment: make every finding survive an adversary before it reaches the user, then decide what may be fixed without asking.

Not polish — cleanup (reuse, dedup, clarity) is `gbase:polish`'s job. Not a GitHub actor — no comments, reviews, replies, or merges, ever.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 이 규칙이 아니라 레포의 기존 관례(`git log`, 최근 PR)를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Scope and mode

Target: explicit paths / range / PR from the caller; else uncommitted changes; else the latest commit. Skip pure renames, dependency bumps, and generated code.

Mode decides how fixes land:

| | **Pre-PR** (from `gbase:go`, or a dirty tree) | **Post-PR** (clean tree + open PR, e.g. from `gbase:monitor`) |
|---|---|---|
| Fixes land as | working-tree edits, no commits — `branch-pr` groups them | one commit per fix, pushed |

The caller's stated mode wins. Without one, a dirty tree means pre-PR even if a PR is open — committing would sweep the user's unrelated edits into a review commit.

## Repo rules

If the repo has a `REVIEW.md` (root or nearest ancestor of the changed files), it governs every stage: hand it to the finder and each skeptic, drop findings on its skip paths, apply its severity overrides and nit cap. Also flag code that breaks a convention `CLAUDE.md` states, and note when `CLAUDE.md` itself contradicts the code.

## Stage 1 — Find

If the caller handed in findings (`gbase:go` passes `candidates already found — start at Stage 2`), skip to Stage 2. Otherwise:

```
Skill(skill: "code-review", args: "medium <target>")
```

- Always pass the target. With none, the built-in reviews the current diff — empty on the clean-tree path, so it reports "nothing found" about a commit it never read.
- `medium` unless the user asked for depth; above it the built-in fans out to a multi-agent workflow at many times the cost, and Stage 2 already removes most of what the extra coverage adds.
- Never `--fix` (bypasses Stage 3), `--comment` (posts to GitHub), or `ultra` (user-triggered and billed — tell the user they can run `/code-review ultra` themselves).
- Drop reuse/simplification/efficiency findings — they're polish's, carry no failure scenario, and would otherwise pass the auto-fix gate and undo restructurings polish chose not to make. Mention them as "noted"; never count or auto-apply them.

If the built-in isn't available, review inline for correctness, error handling, and security across every changed file plus the surrounding code it interacts with; on a larger diff, split the work across parallel sub-agents on the session's model — finding is where model strength buys recall. Every finding needs a concrete failure scenario at `file:line`. Treat these as unverified.

## Stage 2 — Adversarial verify

A skeptic sub-agent must try to refute each finding before it's reported or fixed. Only a `CONFIRMED` finding that will merely be reported (not auto-fixed, not high/critical) skips this — the built-in's own verify is a single non-adversarial pass.

Skeptic prompt:

> Claimed defect: `<finding>` at `file:line`, failure scenario `<scenario>`. Try to refute it: read the code and its callers and find a concrete reason the scenario can't happen (guarded upstream, invariant holds, no caller passes that input, dead branch). Refute the scenario exactly as stated, not a weaker one. If you can't, concede it's real. When uncertain, call it refuted.

One skeptic per low/medium finding — or, with more than ~5 of them, batch 2–3 unrelated findings per skeptic so a large review doesn't spawn a dozen agents; each finding still gets its own verdict. These run with `model: "sonnet"`. High/critical (data loss, security, corruption, crash on a common path) gets three skeptics of its own with different angles, on the session's model (omit `model`) — a wrong refutation silently drops a real bug; a majority refutation kills it. A model the user names for either tier wins. Refuted findings are dropped from the report; keep the count and one-line reasons.

## Stage 3 — Act

**Pre-existing first.** If the defective line isn't in the diff's added/changed hunks (check `git blame` against the base when unsure), label it `pre-existing`: report it, never auto-fix it, and keep it out of the `S survived` / `K for you` counts (it still gets its own table row). Fixing it widens the PR beyond its intent and pins an old bug on this change.

**Fix the class, not the line.** When a survivor is a pattern (a missing `await`, an unchecked `null`, a wrong unit), grep the diff for every other instance and treat them as one finding — otherwise the next round finds the sibling.

**Auto-fix** a survivor only when the fix is mechanical, local (one or two files, small), and fully determined by the finding — no design choice, dependency, schema/migration, API-contract change, or test added/removed. Land it per the mode. Run `gbase:polish` on the touched files before a non-trivial fix is committed or handed back — in pre-PR mode nothing else will polish it.

**Everything else** goes in the report; raise the ones worth fixing before merge with `AskUserQuestion` (`file:line`, failure scenario, 2–3 options). When the caller says *defer, don't ask* (`gbase:go` does, so nothing blocks the PR), return them instead of asking.

If the PR merges before a fix lands, don't push to the merged branch — report it as a follow-up.

## Report

Severity-ordered table `# | severity | file:line | finding | action (auto-fixed / needs decision / pre-existing / noted)`, then `review: F found, R refuted, S survived — A auto-fixed, K for you`. Optionally one line on the sharpest refuted candidate.

## Safety

- No `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, `git stash drop`.
- Undo a bad auto-fix by reversing your own `Edit`, never `git checkout --` / `git restore` — in pre-PR mode the whole change is uncommitted.
- A bug too entangled to fix mechanically is reported, not half-fixed.
