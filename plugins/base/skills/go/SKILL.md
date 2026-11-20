---
name: go
description: "Ships a finished change end to end — reviews and polishes it in parallel, applies verified review fixes, runs the project's fast checks, opens the PR via gbase:branch-pr, and watches it to merge via gbase:monitor. Use when the user says a change is done and wants it shipped, or runs /gbase:go."
allowed-tools: Bash Read Glob Grep AskUserQuestion Skill Agent Edit Write
---

# /gbase:go

Takes a finished change to an open, watched PR: **polish ∥ review → verify → branch-pr → monitor**. `go` only sequences; each sub-skill keeps its own consent and safety rules. Invoking it is the go-ahead to reach a PR: only a diff-caused check failure that resists a mechanical fix and `branch-pr`'s own questions or preview may stop it first. It merges only with `--merge`.

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. 세부: [output-language.md](../../references/output-language.md).

## Read when

| When | Read first |
|---|---|
| Step 1's check prints an `AGENT_` variable | [orchestrated.md](references/orchestrated.md). Under `AGENT_HEADLESS=1` nothing is asked ([headless.md](../../references/headless.md)). |
| Risk `medium` or `high` | [review.md](references/review.md) before Step 2, [verify.md](references/verify.md) at Step 4; on `high` also [high.md](references/high.md) |
| A check fails, or the repo has no verify block | [verify.md](references/verify.md) |
| `--draft`, `--merge`, `--preview`, `--hold-replies`, `--post-replies`, or a finding review deferred | [draft-merge.md](references/draft-merge.md), before Step 5 |

## Steps

### 1. Scope

First run `printenv | grep '^AGENT_'; cat "$(git rev-parse --absolute-git-dir)/gbase/preview-$(git rev-parse HEAD).json" 2>/dev/null`. A `"reviewed": true` line on a clean tree → reviewed and shown: go to Step 5. Uncommitted changes → target them. Clean tree with unpushed `gbase:pause` commits at the tip (`wip:` subject + `Intent:` body) → target their combined diff; `branch-pr` regroups them. Otherwise → the latest commit; if later steps produce no edits there, there is nothing to PR: say so and stop.

Classify the risk the way `branch-pr` does: `high` if it touches a path `REVIEW.md` marks always-high (without one: auth, payments, migrations, CI/release workflows, app config), `low` for docs/copy/tests/flagged additive changes, else `medium`. A user who asked for a deep pass gets `high`'s depth. Report scope and risk in one line.

| risk | finder | skeptics | behavior check |
|---|---|---|---|
| `low` | skip: monitor's self-review covers it during the CI wait | — | skip |
| `medium` | `code-review medium` | `one skeptic for low/medium` | required |
| `high` | `code-review high` | all findings | required |

### 2. Polish ∥ review

Launch an `Agent` (`general-purpose`, `run_in_background: false`) told to run `Skill(skill: "gbase:polish", args: "<in-scope files>; risk: <tier>")`, to leave what polish would ask about unapplied under `awaiting confirm` (it can't ask the user), and to return the report verbatim. An `awaiting confirm` item goes in the final report as a suggestion; a `Comments:` `open` row goes into Step 5's `Deferred:` as `low`. A comment polish deleted stays deleted: that row is its record. Polish's `결정 필요:`/`남은 작업:` lines end the final report verbatim. Polish fails → say so and go on. No `Agent` tool → call `gbase:polish` directly.

On `medium` and `high`, review.md's finder is launched in the same message. No finder on `low`, on `--no-review`, or on a scope review skips anyway (pure rename, dependency bump, generated code).

### 3. Apply review findings

Only when a finder ran, by review.md. Its table doesn't end the turn: go on to Step 4.

### 4. Verification gate

Run the project's own fast checks over the changed scope, each once, on the tree after Step 3: the lines of the `<!-- gbase:verify:start -->` block in `CLAUDE.md` or `AGENTS.md`, at the narrowest scope that covers the diff. A check the route already ran with no edit since counts as run. Native builds, simulators, and E2E suites are CI's, unless the block has a `typecheck (no CI)` line.

Report one line per check, `verify: <command> → pass`, and carry the `behavior:` lines `gbase:work` wrote. All pass on `low` → Step 5. On `medium` and `high` the behavior check in verify.md is still owed: read it now. `--no-verify` skips the step.

### 5. Branch & PR

```
Skill(skill: "gbase:branch-pr", args: "Risk: <tier — reason>; Verification: <Step 4 lines>; Deferred: <severity · introduced|pre-existing · file:line · failure scenario, per finding joined by ' | ', or none>")
```

`Deferred:` lands in the body's `## Review focus`. The report carries its `pr: <url>` line at column 0. A `preview:` line instead → it stopped before the PR: end with its lines, no Step 6.

### 6. Monitor

```
Skill(skill: "gbase:monitor", args: "--no-review")
```

Drop `--no-review` when the pre-PR review didn't run (the `low` row, a finder that failed or never returned) or polish's `Comments:` line has a `fixed` row.
