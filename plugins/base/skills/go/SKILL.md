---
name: go
description: "Ships a finished change end to end — reviews and polishes it in parallel, applies verified review fixes, runs the project's fast checks, opens the PR via gbase:branch-pr, and watches it to merge via gbase:monitor. Review happens before the PR so fixes land in the initial commits. Use when the user says a change is done and wants it shipped, or runs /gbase:go."
allowed-tools: Bash Read Glob Grep AskUserQuestion Skill Edit Write
---

# /gbase:go

Takes a finished change to an open, watched PR: **review ∥ polish → verify → branch-pr → monitor**, back to back. `go` only sequences; each sub-skill keeps its own consent and safety rules, so auto-triggering it never bypasses them.

Review runs *before* the PR so its fixes land in the initial commits — a review after the PR opens turns every finding into an extra commit and a CI rerun. The built-in `code-review` forks to a background agent, so running it alongside polish costs no wall-clock.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## The PR opens without asking

Invoking `go` is the go-ahead to reach a PR. Only two things may stop the flow before it opens: a diff-caused verification failure that isn't mechanically fixable (Step 4), and `branch-pr`'s own "ask only when necessary" cases. Review findings that need a judgment call are carried and raised after the PR exists. Polish keeps its own confirmation for large structural moves.

## Steps

### 1. Scope

Uncommitted changes → target them. Clean tree → target the latest commit (`git show HEAD --name-only`); if later steps produce no edits there, there is nothing to PR — say so and stop. Classify its risk the way `branch-pr` does — `high` if it touches a path `REVIEW.md` marks always-high (without one: auth, payments, migrations, CI/release workflows, app config), `low` for docs/copy/tests/flagged additive changes, else `medium`. Report scope and risk in one line.

### 2. Review (background) ∥ polish

Launch the finder, then polish while it runs:

```
Skill(skill: "code-review", args: "<medium | high per Step 1 risk> <scope from Step 1>")
Skill(skill: "gbase:polish", args: "<in-scope files>")
```

- **Pass the scope explicitly.** With no target the built-in reviews the current diff, which is empty on the clean-tree path — it would report "nothing found" about a commit it never read.
- `medium` by default; `high` when Step 1 rated the change high-risk or the user asked for a deep pass. Not higher by default — above `medium` the built-in fans out to a multi-agent workflow, worth it only where one missed bug is costly.
- Never `--fix` (it would race polish for the same files), `--comment` (no PR yet), or `ultra` (user-triggered and billed).
- Skip the finder on `--no-review` and on scopes review skips anyway (pure rename, dependency bump, generated code).

### 3. Apply review findings

When the findings arrive, hand them to review's judgment stages:

```
Skill(skill: "gbase:review", args: "pre-PR mode; defer, don't ask; candidates already found — start at Stage 2. Findings: <finder output>")
```

Clear fixes come back as working-tree edits (no commits — `branch-pr` groups them); judgment calls come back deferred. Polish rewrote these files after the finder read them, so locate each finding by the code it quotes, not by `file:line`, and re-judge any whose quoted code is gone. Where a review fix and polish collide, the review fix wins.

If the findings haven't arrived when polish finishes, go on to Step 4 and apply them when they land — post-PR mode if the PR is open by then. Skip this step when the finder was skipped. Tally in one line: `review: F found, R refuted, S survived — A fixed, K deferred`.

### 4. Verification gate

Run the project's own checks over the changed scope — polish only validates its own edits, so this is what stops a red PR. Use the `<!-- gbase:verify:start -->` block in `CLAUDE.md` or `AGENTS.md` when present (written by `gbase:setup`; every line was run once except `unverified locally`); otherwise discover them (`CLAUDE.md`/`AGENTS.md`, `package.json` scripts, Makefile, CI workflows) and mention `/gbase:setup` once in the report. Narrowest scope that covers the diff. If the repo defines none, skip and say so; don't invent or install tools.

Keep the gate to fast checks — lint, typecheck, unit tests. Native builds (`pod install`, `xcodebuild`, Gradle assemble), simulator/emulator runs, and E2E suites belong to CI; don't run them here. Two exceptions: a `typecheck (no CI)` line in the verify block — setup writes it only when no CI job builds the app, so it's the repo's only compile gate — and the repo's own verify skill below.

Bias toward shipping:
- Diff-caused and mechanical (type error, lint, missing import) → fix and re-run, at most twice.
- Pre-existing (files the diff didn't touch), flaky, or environment-dependent (no DB, no device, missing env) → note and proceed.
- Diff-caused and still failing after two attempts → `AskUserQuestion` with the output: fix now / open the PR anyway / abort.

**Behavior check.** If the repo has `.claude/skills/verify-*` (from `gbase:create-verify`) and the diff touches a feature in its `features/` map, run that skill for those features only. Same bias as above: an unreachable precondition (no simulator, no test account) is noted and passed; a diff-caused failure of the feature goes through the same fix-twice-then-ask rule.

Skip on `--no-verify`. Report one line per check: `verify: <command> → pass`, `behavior: <feature> → pass (artifacts/verify/<feature>/)`. Hand these lines to `branch-pr` as the PR's `## Evidence`.

### 5. Branch & PR

```
Skill(skill: "gbase:branch-pr", args: "Risk: <tier — reason>; Verification: <Step 4 lines>")
# invoked with --draft → args: "--draft Risk: …; Verification: …"
```

`branch-pr` owns branching, commit grouping, push, PR body, and its `compat-check` rollout section; all its safety rules apply.

### 6. Monitor

```
Skill(skill: "gbase:monitor", args: "--no-review")            # add --draft when invoked with --draft
```

Drop `--no-review` if the pre-PR review didn't actually run (finder skipped, failed, or never returned), so monitor's self-review covers the diff.

Then surface the deferred findings: a severity-ordered table (`file:line`, failure scenario, what the fix takes), with `AskUserQuestion` on any worth resolving before merge. Monitor never received them, so `go` applies, commits, and pushes any fix the user accepts. Under `--draft`, pass monitor the count of unresolved deferred findings so it holds the ready flip until they're resolved.

## On failure

- Polish fails → surface it; ask whether to continue without it or abort.
- `branch-pr` fails → stop, print `git status`, and point at the backup stash (`git stash apply stash@{0}`, not `pop`).
- Monitor can't start (no `gh` auth, no PR) → surface and stop; the PR is already up.

## Usage

```
/gbase:go               # review ∥ polish → verify → PR → monitor
/gbase:go --draft       # open a draft PR; monitor flips it to ready when CI is green
/gbase:go --no-review   # skip the pre-PR review
/gbase:go --no-verify   # skip the local check gate; let CI judge
```
