---
name: go
description: "Ships a finished change end to end — reviews and polishes it in parallel, applies verified review fixes, runs the project's fast checks, opens the PR via gbase:branch-pr, and watches it to merge via gbase:monitor. Review happens before the PR so fixes land in the initial commits. Use when the user says a change is done and wants it shipped, or runs /gbase:go."
allowed-tools: Bash Read Glob Grep AskUserQuestion Skill Agent Edit Write
---

# /gbase:go

Takes a finished change to an open, watched PR: **review ∥ polish → verify → branch-pr → monitor**, back to back. `go` only sequences; each sub-skill keeps its own consent and safety rules, so auto-triggering it never bypasses them.

Review runs *before* the PR so its fixes land in the initial commits — a review after the PR opens turns every finding into an extra commit and a CI rerun. The finder runs in a background agent, so running it alongside polish costs no wall-clock.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## The PR opens without asking

Invoking `go` is the go-ahead to reach a PR. Only two things may stop the flow before it opens: a diff-caused verification failure that isn't mechanically fixable (Step 4), and `branch-pr`'s own "ask only when necessary" cases. Review findings that need a judgment call are carried and raised after the PR exists. Polish keeps its own confirmation for large structural moves. Merging happens only with `--merge` — passed when the user asked to merge, or the project's instructions say to; never add it by default. Without it, `go` stops at a watched PR.

## Run by an orchestrator

Step 1 reads the `AGENT_*` variables once (`printenv | grep '^AGENT_'`); with none set, nothing in this section or the `AGENT_*` notes below applies. They are defined in [orchestrator.md](../../references/orchestrator.md). Under `AGENT_HEADLESS=1` nothing is asked: follow [headless.md](../../references/headless.md), using the defaults marked *headless:* below.

## Steps

### 1. Scope

Uncommitted changes → target them. Clean tree with unpushed `gbase:pause` commits at the tip (`wip:` subject + `Intent:` body) → target their combined diff and ship it — `branch-pr` regroups them. Otherwise clean tree → target the latest commit (`git show HEAD --name-only`); if later steps produce no edits there, there is nothing to PR — say so and stop. Classify its risk the way `branch-pr` does — `high` if it touches a path `REVIEW.md` marks always-high (without one: auth, payments, migrations, CI/release workflows, app config), `low` for docs/copy/tests/flagged additive changes, else `medium`. A user who asked for a deep pass gets `high`'s depth. Report scope and risk in one line.

The tier sets how much defect-hunting and behavior checking runs. Polish isn't in the table: it runs the same on every tier (its own skip rules still apply).

| risk | finder | Step 3 skeptics | behavior check |
|---|---|---|---|
| `low` | skip — monitor's self-review covers it during the CI wait (*headless:* `code-review low`) | — (*headless:* `one skeptic for low/medium`) | skip — fast checks only |
| `medium` | `code-review medium` | `one skeptic for low/medium` | required |
| `high` | `code-review high` | all findings | required |

Headless runs review `low` before the PR because they often end before any monitor self-review — under `AGENT_SHIP_OWNER=orchestrator` there is no Step 6.

Under `AGENT_SHIP_OWNER=orchestrator`, or `AGENT_HEADLESS=1` with any owner, a clean tree targets every commit on the branch that isn't in the base (`<base>...HEAD`; base = `origin/<default>` when it exists, else the local default branch) — the orchestrator's agent may have committed as it worked.

### 2. Review (background) ∥ polish

Launch the finder in the background, then polish while it runs — both calls in one message:

```
Agent(subagent_type: "general-purpose", run_in_background: true, description: "review finder",
      prompt: "Run Skill(skill: \"code-review\", args: \"<effort> <scope from Step 1>\") and return its findings verbatim. Edit nothing.")
Skill(skill: "gbase:polish", args: "<in-scope files>")
```

- **Don't call `code-review` directly here.** Under `claude -p` a forked skill blocks its caller until it finishes, which turned review ∥ polish into review → polish in headless runs.

- **Pass the scope explicitly.** With no target the built-in reviews the current diff, which is empty on the clean-tree path — it would report "nothing found" about a commit it never read.
- Effort per the Step 1 table. Never above `high` — above `medium` the built-in already fans out to a multi-agent workflow, worth it only where one missed bug is costly.
- Never `--fix` (it would race polish for the same files), `--comment` (no PR yet), or `ultra` (user-triggered and billed).
- Skip the finder per the table's `low` row (not when headless), on `--no-review`, and on scopes review skips anyway (pure rename, dependency bump, generated code).

### 3. Apply review findings

When the findings arrive, hand them to review's judgment stages:

```
Skill(skill: "gbase:review", args: "pre-PR mode; defer, don't ask; candidates already found — start at Stage 2. Findings: <finder output>")
```

On `medium` (and headless `low`), insert `; one skeptic for low/medium` right after `start at Stage 2`.

Clear fixes come back as working-tree edits (no commits — `branch-pr` groups them); judgment calls come back deferred. Polish rewrote these files after the finder read them, so locate each finding by the code it quotes, not by `file:line`, and re-judge any whose quoted code is gone. Where a review fix and polish collide, the review fix wins.

If the findings haven't arrived when polish finishes, wait for them before Step 4 — the gate then runs once on the final tree instead of again after the fixes. If the finder fails, go on without it (Step 6 drops `--no-review`). Skip this step when the finder was skipped. Tally in one line: `review: F found, R refuted, S survived — A fixed, K deferred`. Review's table and tally are this step's output, not `go`'s report: go on to Step 4 in the same turn. Under `claude -p` a turn that ends there ends the run once no background task is left to wake it — one headless `work` run stopped on the table with the change uncommitted and no PR.

### 4. Verification gate

Run the project's own checks over the changed scope — polish only validates its own edits, so this is what stops a red PR. Use the `<!-- gbase:verify:start -->` block in `CLAUDE.md` or `AGENTS.md` when present (written by `gbase:setup`; every line was run once except `unverified locally`); otherwise discover them (`CLAUDE.md`/`AGENTS.md`, `package.json` scripts, Makefile, CI workflows) and mention `/gbase:setup` once in the report. Narrowest scope that covers the diff — the full suite is CI's when a scoped run covers it. Run each check once, on the tree after Step 3; a check the route already ran with no edit since counts as run. If the repo defines none, skip and say so; don't invent or install tools.

Keep the gate to fast checks — lint, typecheck, unit tests. Native builds (`pod install`, `xcodebuild`, Gradle assemble), simulator/emulator runs, and E2E suites belong to CI; don't run them here. Two exceptions: a `typecheck (no CI)` line in the verify block — setup writes it only when no CI job builds the app, so it's the repo's only compile gate — and the repo's own verify skill below.

Bias toward shipping:
- Diff-caused and mechanical (type error, lint, missing import) → fix and re-run, at most twice — re-run the failing file or case first, then the scoped command once.
- Pre-existing (files the diff didn't touch), flaky, or environment-dependent (no DB, no device, missing env) → note and proceed.
- Diff-caused and still failing after two attempts → `AskUserQuestion` with the output: fix now / open the PR anyway / abort. *headless:* open it anyway with the failure in Evidence — as a `--draft` PR when the agent owns the PR.

**Behavior check** — required per the Step 1 table when the diff changes what a user or caller observes. It runs once per change, not once per skill:

- **Reuse the route's run.** Take the passing `behavior:` lines `gbase:work` wrote for this task as-is, except for a feature whose files a review fix touched after that run — re-run that one. A route `skip` line is not reused; try the feature here.
- **Otherwise run it here.** The repo's verify skill — `.claude/skills/verify-*/` (from `gbase:create-verify`) or `.claude/skills/verify/` (pstack's generator), at the root or in the touched package — for the features in its `features/` map that the diff touches. Without one, a CLI or script run that exercises the change and needs no build, device, or server start; don't build a harness for it.
- **Required means evidence or a reason.** An unreachable precondition (no simulator, no test account, no such run) is `behavior: skip — <reason>`, noted and passed. A diff-caused failure goes through the same fix-twice-then-ask rule.
- **Say what it ran on.** When a check ran on a chosen input — a fixture, sample files, a simulator — and the bug report or real use has a different kind (resolution, format, metadata, device), name both: 1024px messenger copies passed while the phone's full-size originals still failed, and the report never said the inputs differed.

Skip on `--no-verify`. Report one line per check: `verify: <command> → pass`, `behavior: <feature> → pass (<evidence dir>)`, adding `(input: <what it ran on>; differs: <difference>)` when the point above applies. Hand these lines to `branch-pr` as the PR's `## Evidence`.

With `AGENT_EVIDENCE_FILE` set, append the [evidence lines](../../references/orchestrator.md#evidence-file) as results become final: one per check command and per behavior feature (with `input` when it ran on a chosen input), plus one each for review (after Step 3) and polish. A skipped step still gets its `skip` line.

### 5. Branch & PR

```
Skill(skill: "gbase:branch-pr", args: "Risk: <tier — reason>; Verification: <Step 4 lines>; Deferred: <severity · introduced|pre-existing · file:line · failure scenario, per finding joined by ' | ', or none>")
# invoked with --draft → args: "--draft Risk: …; Verification: …; Deferred: …"
```

`branch-pr` owns branching, commit grouping, push, PR body, and its `compat-check` rollout section; all its safety rules apply. The deferred findings become items in the body's `## Review focus`.

Under `AGENT_SHIP_OWNER=orchestrator` the args start with `Ship-owner: orchestrator; PR-body-file: <$AGENT_PR_BODY_FILE, else $(git rev-parse --absolute-git-dir)/gbase/pr-body.md>; ` and `branch-pr` commits locally and writes the draft instead of pushing. Then stop: no Step 6. The report ends with branch-pr's `ship:` and `PR 본문 초안:` lines and the deferred-findings table.

Otherwise, once the PR exists, the report carries `pr: <url>` at column 0 — `branch-pr`'s, or `gh pr view --json url -q .url` when it pushed to a PR that already existed — so an orchestrator can read it.

### 6. Monitor

```
Skill(skill: "gbase:monitor", args: "--no-review")            # add --draft / --merge when invoked with them
```

*headless:* the owner is the agent here (an orchestrator owner stopped at Step 5). Add `--until-settled` to the args (the `--no-review` rule below still applies) instead of running the persistent watch, which has no one to end it under `claude -p`; monitor pushes its fixes, replies, and ends with one `settle:` line. Never pass `--merge` in this mode — it never merges; a requested merge becomes a `결정 필요:` line for the caller. A `--draft` PR stays a draft; say so in a `결정 필요:` line. The deferred-findings paragraph below shrinks to its table: nothing is asked or pushed after monitor, so the `settle:` verdict stays true for the head it names.

Drop `--no-review` if the pre-PR review didn't actually run (finder skipped, failed, or never returned), so monitor's self-review covers the diff — on `low` that review lands in the CI wait instead of before the PR.

Then surface the deferred findings: a severity-ordered table (`file:line`, failure scenario, what the fix takes), with `AskUserQuestion` on any worth resolving before merge. Monitor never received them, so `go` applies, commits, and pushes any fix the user accepts, then drops that item, and its count, from the PR body's `## Review focus` or its folded list, switching to the `[!NOTE]` box when none remain (`gh pr edit --body`, after `gbase:unslop` like the first body). Under `--draft`, pass monitor the count of unresolved deferred findings so it holds the ready flip until they're resolved. Under `--merge`, settle the deferred findings first (fix or decline each); pass `--merge` only once none remain open, plus `verified-locally` when Step 4 passed this run — otherwise drop `--merge` and say why the PR stays open.

## On failure

- Polish fails → surface it; ask whether to continue without it or abort. *headless:* continue without it.
- `branch-pr` fails → stop, print `git status`, and point at the backup stash (`git stash apply stash@{0}`, not `pop`).
- Monitor can't start (no `gh` auth, no PR) → surface and stop; the PR is already up (`pr:` line still in the report).

## Usage

```
/gbase:go               # review ∥ polish → verify → PR → monitor
/gbase:go --draft       # open a draft PR; monitor flips it to ready when CI is green
/gbase:go --merge       # also merge once CI is green and nothing is outstanding
AGENT_SHIP_OWNER=orchestrator claude -p "/gbase:go"   # stop after local commits + a PR body draft; another program pushes
/gbase:go --no-review   # skip the pre-PR review
/gbase:go --no-verify   # skip the local check gate; let CI judge
```
