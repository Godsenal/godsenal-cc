---
name: review
description: "Adversarial code review of the current change. Stage 1 replicates the built-in code-review's dimensions (correctness & edge cases, bugs/regressions/missing error handling, security & data handling, clarity & consistency, test/doc gaps) as a high-signal finder. Stage 2 is adversarial verification — each finding is handed to independent skeptics that try to refute it with a concrete counter-scenario, and anything they kill is dropped. Survivors are classified like reviewer comments: clear+local ones auto-fixed in their own commits, the rest reported to the user in a severity table. Local-only — never posts to GitHub. Replaces the built-in `code-review` for the self-review role in `gbase:monitor` and `gbase:go`. Invoke via /gbase:review, or as monitor's post-PR self-review."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Skill
---

# /gbase:review

Adversarial code review of the current change. Find real defects the way the built-in `code-review` skill did, then **make each finding survive an adversary before it reaches the user** — the verification stage exists to kill plausible-but-wrong findings, which is where an unverified review wastes the most of the user's time.

This skill exists because the built-in `code-review` is no longer model-invocable, so `gbase:monitor` / `gbase:go` can't call it. `gbase:review` is the drop-in replacement for that self-review role, with an adversarial verify pass added on top.

Model-invocable: run explicitly via `/gbase:review`, or let `gbase:monitor` invoke it as the post-PR self-review. Auto-triggering only produces a **local report + clear-and-local auto-fixes** — never a GitHub write, never a merge.

## What this is not

- **Not polish.** `gbase:polish` is behavior-preserving cleanup (reuse, dedup, clarity). `gbase:review` hunts for *defects* — bugs, regressions, security holes, missing handling. If the only thing wrong is slop, that's polish's job; don't duplicate it here.
- **Not a GitHub actor.** Read-only on GitHub: no comments, no reviews, no replies, no merge. Findings go to the user; fixes show up as local commits.

## Scope

Resolve the change under review, in this order:

```bash
git status --short
git diff --stat HEAD
git diff --stat @{upstream}...HEAD   # if branched (no upstream: main...HEAD, then HEAD~1)
```

- **Caller passes explicit paths / a range / a PR** → scope to those (monitor passes the PR diff).
- **Uncommitted changes present** → review those files.
- **Clean working tree** → review the latest commit (`git show HEAD --name-only`).

**Cover every changed file.** Read the changed ranges *and* enough of the surrounding code to judge them in context — a bug is often the interaction between the diff and code it didn't touch. Skip entirely on: pure rename/move commits, dependency bumps, generated code (lockfiles, OpenAPI clients, compiled assets).

## Stage 1 — Find (built-in dimensions, high-signal)

Review each changed file against the rest of the codebase along the **same dimensions the built-in `code-review` used**:

- **Correctness and edge cases** — off-by-one, null/empty/boundary inputs, unhandled branches, wrong operator, inverted condition, copy-paste of the wrong variable.
- **Bugs, regressions, and missing error handling** — a path that used to work and now doesn't, a thrown error with no catch on a boundary that needs one, an unawaited promise, a resource never released.
- **Security and data handling** — injection, missing authz/ownership check, secret in the diff, unsafe deserialization, PII logged, SSRF, a trust boundary crossed without validation.
- **Clarity, naming, and consistency** with surrounding code — only when it can actually mislead a future reader into a bug, not pure taste.
- **Tests and documentation gaps the change introduces** — new behavior with no test, a contract change no doc reflects.

Posture — **match the built-in's signal bar**: prefer fewer, higher-signal findings over many minor nits. Do not flag things that are already correct. Each finding must name a **concrete failure scenario**: specific inputs/state → wrong output or crash, at `file:line`. "This could be fragile" without a scenario is not a finding — either make it concrete or drop it.

For a non-trivial diff (more than a couple of files), run the finder as a **parallel fan-out** — spawn sub-agents via `Agent` (`subagent_type: general-purpose`), each handed the full diff and one dimension above, each returning a structured list `{file, line, severity, finding, failure_scenario}` and editing nothing. Dedupe their results by `file:line` before Stage 2. For a tiny diff, find inline. Either way, the output of Stage 1 is a deduped candidate list — **candidates, not verdicts.**

## Stage 2 — Adversarial verify

Every candidate must survive an adversary before it reaches the user. This is the point of the skill.

For each candidate, spawn independent skeptic sub-agent(s) via `Agent` — **prompted to refute, not to confirm**:

> Here is a claimed defect: `<finding>` at `file:line`, with failure scenario `<scenario>`.
> Your job is to **refute** it. Read the code and its callers. Produce a concrete reason the scenario cannot actually happen (guarded upstream, invariant holds, caller never passes that input, framework handles it, dead branch). If after genuinely trying you cannot refute it, concede it is real. Default to **refuted** when uncertain — a false alarm costs more than a miss here.

Scale the adversary to the stakes:

- **Low / medium severity** → one skeptic. Survives only if the skeptic concedes it's real.
- **High / critical severity** (data loss, security, corruption, crash on a common path) → a **3-skeptic panel**, each with a distinct lens where it helps (does-it-reproduce / is-it-guarded-upstream / does-a-caller-prevent-it). Kill the finding if a **majority** refute it.

A candidate that is refuted is **dropped silently** — it never reaches the user. Keep a count of `found / refuted / survived` for the tally. When a skeptic refutes, capture its one-line reason; a couple of the sharpest refutations are worth showing the user as "considered and dismissed" so the review reads as thorough, not thin.

Do not strawman your own candidates to kill them: the skeptic must refute the **exact** scenario Stage 1 stated, not a weaker one. And do not let Stage 1's confidence survive Stage 2 unexamined — a finding that "looks obviously right" but that no skeptic could produce a reproducing input for is exactly the kind this stage is here to catch.

## Stage 3 — Classify & act (local only)

Feed every **survivor** through the same clear-vs-ambiguous split `gbase:monitor` uses for reviewer comments:

**Clear → auto-fix** when ALL hold:

- Mechanical and local (one or two files, small diff): missing `await`, inverted condition, wrong-variable copy-paste, an obvious missing null guard on a path the scenario proves is reachable.
- The fix is fully determined by the finding — no design choice, no new dependency, no schema/migration, no API-contract change.
- No test is added or removed to make it pass (beyond the fix itself).

Apply each clear fix as **its own commit** with a message naming the defect. Run [post-fix polish](#post-fix-polish) on non-trivial auto-edits before committing. If the change is under an active PR watch and merges before a fix lands, don't push to the merged branch — report it as a follow-up-PR candidate instead.

**Everything else → report + ask.** Architecture, behavior change, security trade-offs, anything touching tests/schemas/config, or any survivor where the fix is a judgment call: put it in the report, and surface the ones worth fixing before merge via `AskUserQuestion` (include `file:line`, the failure scenario, and 2–3 concrete options).

### Post-fix polish

Before committing any non-trivial auto-fix, run:

```
Skill(skill: "gbase:polish", args: "<touched files>")
```

Skip for one-line mechanical fixes.

## Report

One organized report when the pass finishes — **local, nothing posted to GitHub**:

- A severity-ordered table: `# | severity | file:line | finding | action (auto-fixed <sha> / needs decision / noted)`.
- A one-line tally: `review: F found, R refuted, S survived — A auto-fixed, K for you`.
- Optionally, one line naming the sharpest refuted candidate(s) so the user sees what was dismissed and why.

If a called-out `--no-review` reached this skill, or the diff is out of scope (pure rename, dep bump, generated code), say so in one line and stop.

## Safety rules

Inherits `gbase:monitor`'s rules:

- Prohibited: `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, `git stash drop`.
- Revert a bad auto-fix by reversing your **own** `Edit`, never `git checkout --`/`git restore` (which would wipe the user's uncommitted work).
- Each auto-fix is its own commit; stop and surface on any error rather than retrying destructively.
- Read-only on GitHub at all times — no comments, reviews, replies, or merges.
- If a real correctness bug is too entangled to fix mechanically, report it; don't half-fix it.
