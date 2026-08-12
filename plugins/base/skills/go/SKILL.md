---
name: go
description: "Finish code changes in one shot — launch the built-in code-review in the background, run /gbase:polish on the current diff while it works, apply the verified review findings, run the project's own lint/typecheck/tests as a pre-push gate, then /gbase:branch-pr and /gbase:monitor until merge. Review runs before the PR opens, so fixes land in the initial commits instead of as churn on an open PR — and it costs no wall-clock because it runs concurrently with polish. Invoke manually with /gbase:go, or let the model auto-trigger it when the user signals a change is done and wants it shipped."
allowed-tools: Bash Read Glob Grep AskUserQuestion Skill Edit Write
---

# /gbase:go

Wraps up a working session: **review + polish** (concurrently), a **verification gate**, **branch-pr** to ship it, and **monitor** to babysit CI until merge. The steps run back-to-back without extra confirmation between them — each sub-skill's own confirmations still apply.

Model-invocable: the user can trigger it via `/gbase:go`, and the model may auto-trigger it when the user signals a chunk of work is finished and wants it shipped. Because each side-effecting step (`branch-pr` push/PR, `monitor` auto-fixes) carries its own consent and safety rules, those still gate the side effects — `go` itself just sequences them.

## Why review runs before the PR

The built-in `code-review` **forks to a background agent**, so it costs `go` no wall-clock: launch it first, let it work while polish's three lens agents and structural pass churn, and collect its findings before the first commit.

That timing is the whole point. A review that runs *after* the PR opens turns every finding into an extra commit on an open PR — reviewers see churn, CI reruns per fix, and the PR's first impression is a red build. Running it before `branch-pr` means the fixes are simply part of the change.

`monitor` therefore gets `--no-review`: the review already happened. Monitor's own self-review stays for the case `go` doesn't cover — attaching to a PR someone else (or an earlier session) opened.

## Autonomy contract — the PR still opens without asking

The pre-PR review must **not** add a gate in front of PR creation. Invoking `go` is the go-ahead to reach a PR; everything before Step 6 either fixes itself or gets carried into the PR and raised afterward.

Exactly two things may stop the flow before the PR opens:

1. **A verification failure that the diff clearly caused and that isn't mechanically fixable** — a genuinely broken change (see Step 5). Pushing it would open a red PR the user has to babysit anyway.
2. **`branch-pr`'s own narrow "ask only when necessary" cases** — a secret in the diff, unrelated WIP, an ambiguous PR split, remote ambiguity.

Everything else is non-blocking. In particular: review findings that need a judgment call are **not** asked before the PR. They are carried and surfaced after the PR is open, where the user answers them at their own pace with `monitor` already watching. Polish keeps its own `AskUserQuestion` on large structural moves.

## Flow

1. **Detect scope** — decide whether the run targets the uncommitted diff or the latest commit.
2. **Launch review (background)** — fire the built-in `code-review` finder; do not wait.
3. **Polish** — invoke `gbase:polish` (deslop → structural) while the finder runs.
4. **Apply review findings** — hand the finder's output to `gbase:review` for adversarial verification and the clear-vs-ambiguous gate.
5. **Verify** — run the project's own lint/typecheck/tests over the changed scope. Nothing gets pushed on a red gate without the user's say.
6. **Branch & PR** — invoke `gbase:branch-pr` to back up, branch, group commits, push, and open a PR.
7. **Monitor** — invoke `gbase:monitor --no-review` to watch CI and reviews until merge.

## Execution

### Step 1 — Detect scope

```bash
git status --short
git diff HEAD --stat
git log --oneline -1
```

- **Uncommitted changes present** → steps 2–5 target those files; branch-pr runs afterward.
- **Clean working tree** → target the most recent commit (`git show HEAD --name-only`). If steps 3–4 introduce new edits, branch-pr still runs on those; if they don't, skip branch-pr and tell the user there's nothing to PR.

Report the detected scope in one line, then proceed without waiting.

### Step 2 — Launch the review finder (background, don't wait)

Skip entirely on `--no-review`, and on scopes review skips anyway (pure rename, dependency bump, generated code).

```
Skill(skill: "code-review", args: "medium <the scope from Step 1>")
```

**Pass the scope explicitly.** With no target the built-in reviews *the current diff* — which is empty on the clean-tree path, so it would return zero findings about a commit nothing ever read, and Step 4 would report "review found nothing" in good faith. Pass the commit range or paths Step 1 resolved.

**Move straight to Step 3 — do not block on it.** The result is not a return value you can await: the skill runs in the background and its findings arrive later as a task notification. You don't poll for it and you don't wait; you keep working, and the notification reaches you when it lands.

Use `medium` unless the user asked for a deep pass. Above `medium` the built-in routes to a multi-agent workflow that fans out to dozens of agents — still background, so `go`'s timing is unchanged, but an order of magnitude more expensive on a flow that runs on every shipped change.

Rules, inherited from `gbase:review`:

- **Never `--fix`** — it would edit the working tree concurrently with polish, racing it for the same files. The finder must stay read-only; fixes are applied in Step 4 by the main agent.
- **Never `--comment`** (no PR exists yet) and **never `ultra`** (user-triggered and billed — you cannot launch it).

### Step 3 — Polish (while the finder runs)

```
Skill(skill: "gbase:polish", args: "<list of in-scope files>")
```

Deslop pass (3-lens fan-out) then structural pass, both behavior-preserving. Larger structural moves prompt via `AskUserQuestion`; smaller ones apply directly. Wait for it to finish, then summarize what landed in one or two sentences.

### Step 4 — Apply the verified review findings

**Skip this step whenever Step 2 was skipped** (`--no-review`, or a scope review skips anyway) and go straight to Step 5 — there is no finder to wait for, and calling `gbase:review` with an empty list would make it run the finder `--no-review` was meant to suppress.

**If the findings haven't arrived by the time polish finishes, don't stall for them.** Continue to Step 5 and run this step whenever the notification lands. If that turns out to be after the PR is open, hand the findings to `gbase:review` in *post-PR* mode instead, and don't claim in Step 7 that the diff was reviewed pre-PR.

**Re-anchor every finding before applying it.** The finder read the tree as it was at Step 2; polish then rewrote the same files. Line numbers have moved. Locate each finding by the **code it quotes**, not by `file:line` — if the quoted code no longer exists, polish removed or rewrote it, so re-judge the finding against the current text instead of patching whatever now sits at that line number. Applying a stale coordinate is how an `await` gets inserted on the wrong call.

Otherwise, hand the findings straight to review's judgment stages:

```
Skill(skill: "gbase:review", args: "pre-PR mode; defer, don't ask; candidates already found — start at Stage 2. Findings: <finder output>")
```

`gbase:review` skips its own Stage 1 (the candidates are already in hand) and runs its verify + classify stages on them. The part `go` depends on: **fixes land as working-tree edits, not commits** — `branch-pr` groups them into the initial commits in Step 6.

**Judgment calls do not block the PR** (see [Autonomy contract](#autonomy-contract--the-pr-still-opens-without-asking)). Tell `gbase:review` to **defer, not ask**: it returns the ambiguous survivors instead of raising `AskUserQuestion`, and `go` carries them to Step 7 and surfaces them once the PR is open.

If polish and a review fix touch the same code, the review fix wins: polish is cosmetic, the review finding is a defect.

**Polish the review fixes themselves.** Step 3's polish ran before these edits existed, so `gbase:review` runs `gbase:polish` on the files it touched before handing them back — otherwise a review fix ships unpolished inside the PR's initial commits.

Report the tally in one line: `review: F found, R refuted, S survived — A fixed, K deferred to after the PR`.

### Step 5 — Verification gate (before anything is pushed)

Run the project's *own* checks over the changed scope. This is not polish's verification — that one only validates polish's own edits and reverts them on failure, so a failure that was already in the user's code sails straight through to CI. This gate is what stops a red PR.

**Find the commands, don't invent them.** First match wins:

1. `CLAUDE.md` / `AGENTS.md` — if the repo documents its check commands, use exactly those and stop looking
2. `package.json` scripts — `typecheck` / `tsc`, `lint`, `test`
3. `Makefile` targets, `justfile` recipes, `.github/workflows/*.yml` (whatever CI runs is the bar to clear)
4. Language defaults when nothing is configured: `tsc --noEmit`, `ruff check` + `mypy`, `cargo check`, `go build ./...`

**Run the narrowest scope that covers the diff** — a focused test file over the whole suite, changed paths over the whole tree — and fall back to the project-wide command only when the tool can't be scoped. If the project has no checks at all, skip the gate and say so in one line; don't invent a command or install a tool.

**On failure — bias toward shipping.** This gate exists to stop a *broken* change, not to slow down a working one:

- **Caused by a changed file, and the fix is mechanical** (type error, lint autofix, missing import, bad formatting) → fix it and re-run. **At most two attempts** on the same failure; a third means it isn't mechanical.
- **Clearly pre-existing** — the failure is in files the diff never touched → note it in one line and **proceed**. Don't fix unrelated breakage inside a ship flow, and don't hold the user's PR for it.
- **Flaky, environment-dependent, or a missing local dependency** (no DB, no env vars, network-gated test) → note it and **proceed**. CI is the authority on those, not the local machine.
- **Caused by the diff and not mechanically fixable after two attempts** → this is the one case worth stopping for. `AskUserQuestion` before `branch-pr` with the failing output and three options: fix it now / open the PR anyway and let CI carry it / abort.

Skip the gate entirely on `--no-verify`. Report the result in one line either way: `verify: pnpm typecheck + vitest run src/… → pass`.

### Step 6 — Branch & PR

If Step 1 found uncommitted changes — or if steps 3–4 introduced new ones — invoke, **forwarding `--draft` when the user passed it**. Only `branch-pr` can open the PR as a draft, and this is the last moment it can be said:

```
Skill(skill: "gbase:branch-pr")                    # plain
Skill(skill: "gbase:branch-pr", args: "--draft")   # when invoked as /gbase:go --draft
```

That skill owns the rest and runs **fully autonomously** — it decides the branch name, commit grouping, and PR body itself, pushes, and opens the PR without step-by-step confirmation, stopping only for its narrow "ask only when necessary" cases (secret in the diff, unrelated WIP, ambiguous PR split, remote ambiguity). As part of PR creation it invokes `gbase:compat-check`; if a sequenced rollout is needed (migrate-before-deploy, new required env, etc.), it injects a `## Rollout / Deploy order` section into the PR body and flags it to you.

All safety rules from `gbase:branch-pr` apply unchanged — `go` is a pure wrapper.

If Step 1 found no changes and steps 3–4 produced no edits, stop here and tell the user.

### Step 7 — Monitor

Immediately after `branch-pr` returns a PR URL:

```
Skill(skill: "gbase:monitor", args: "--no-review")            # plain
Skill(skill: "gbase:monitor", args: "--no-review --draft")    # when invoked as /gbase:go --draft
```

`--no-review` because Step 4 already reviewed this diff (see [Why review runs before the PR](#why-review-runs-before-the-pr)). **Drop that flag if the review didn't actually happen** — the finder failed, never returned, or Step 2 was skipped — so monitor's own self-review covers the diff instead of it going unreviewed entirely.

**Surface the deferred findings now.** Once the PR URL is in hand, print the judgment calls Step 4 held back — a severity-ordered table with `file:line`, the failure scenario, and what it would take to fix — and raise `AskUserQuestion` on any that should be resolved before merge.

**`go` owns these fixes, not monitor.** Monitor was invoked with `--no-review` and never received them; they exist only locally and were never posted to GitHub, so they are in neither its CI sweep nor its review-comment sweep. When the user agrees to a fix, apply it here, commit it, and push it to the PR branch yourself. Don't hand it off — nothing is listening.

**Under `--draft`, tell monitor about them.** Monitor flips a draft to ready on CI green; a deferred high-severity finding would otherwise be announced ready-for-review still unaddressed. Pass the count of unresolved deferred findings so monitor holds the flip until they're resolved (see monitor's `--draft` flow).

Monitor resolves the PR, sweeps CI + reviews, and starts a persistent `Monitor` until merge or close. It auto-fixes clear CI failures (lint, format, type, missing imports) and applies clearly-required review comments; ambiguous items get `AskUserQuestion`. Under `--draft`, `branch-pr` (Step 6) already opened the PR as a draft; monitor flips it to ready once CI is green.

If `branch-pr` was skipped (no changes), skip this step too.

If the user wants to ship without ongoing monitoring, they can stop the Monitor with `TaskStop` mid-flight; `branch-pr`'s work is already on the remote.

## Error handling

- **Polish and the review finder both produce nothing, tree was already clean** → stop, inform the user.
- **Polish fails** → surface the error; ask whether to continue with pre-existing changes or abort.
- **Review finder fails or never returns** → don't block the ship path. Report that review was skipped, continue from Step 5, and **drop `--no-review` from the Step 7 monitor call** so monitor's own self-review covers this diff — otherwise it goes unreviewed entirely.
- **Verification gate fails** → see Step 5. Pre-existing, flaky, and environment-dependent failures are noted and passed; only a diff-caused failure still red after two mechanical fix attempts blocks `branch-pr`, and only until the user chooses.
- **Branch-pr fails at any step** → stop, print `git status`, give recovery instructions:
  - Restore from backup stash: `git stash apply stash@{0}` (apply, not pop — keep the backup)
  - Delete the created branch: `git checkout main && git branch -D <branch-name>`
- **Monitor fails to start** (no `gh` auth, no PR resolvable) → surface the error and stop; `branch-pr`'s output is unaffected.

## Usage

```
/gbase:go               # review ∥ polish → verify → PR → monitor
/gbase:go --draft       # open a draft PR; monitor flips it to ready when CI is green
/gbase:go --no-review   # skip the pre-PR review entirely
/gbase:go --no-verify   # skip the local lint/typecheck/test gate; let CI be the judge
```

Typical session:

```
User: /gbase:go

Claude: Detected 4 uncommitted files:
  M  src/db/schema.ts
  M  src/app/api/users/route.ts
  A  src/components/UserProfile.tsx
  A  src/components/UserProfile.test.tsx

Launched code-review (background). Running /gbase:polish on these files…
[deslop strips 3 redundant comments + one defensive try/catch in UserProfile.tsx]
[structural pass inlines a single-caller helper in route.ts]

review: 4 found, 2 refuted, 2 survived — 1 fixed (missing await in route.ts:41), 1 deferred.
verify: pnpm typecheck + vitest run src/components → pass

Proceeding to /gbase:branch-pr.
Branch: feat/user-profile → committed, pushed.
compat-check: ✅ no special deploy ordering.
[branch-pr opens PR #142 — review fixes are already in the initial commits]

Proceeding to /gbase:monitor --no-review for PR #142.
Subscribing to CI + reviews (auto-fixing clear failures; will ping on anything ambiguous).

Deferred from review — your call, nothing is blocked:
  1 | medium | schema.ts:22 | new column has no index; the users list query filters on it
```
