---
name: compat-check
description: "Scan a code change for backward-compatibility hazards and tell you the safe deploy/script order. Reads a diff (uncommitted, a commit range, or a PR) and flags migrations, API/contract changes, queue/event schema changes, new required env/secrets, feature flags, and backfill scripts — then emits an ordered rollout runbook. Read-only: it never edits code, runs scripts, or deploys. Use when asked about deploy order, rollout order, backward/forward compatibility, '배포 순서', '하위호환', migration ordering, or 'is this change safe to ship in one deploy'. Auto-invoked by gbase:branch-pr / gbase:go to add a Rollout section to the PR body."
allowed-tools: Bash Read Glob Grep AskUserQuestion
---

# /gbase:compat-check

Analyze a change for **backward-compatibility hazards** and produce the **order** in which things must
ship — migrations, config, deploys, backfill scripts, flag ramps, and any follow-up cleanup. The goal is
to answer one question: *can this go out in a single deploy, or does it need a sequenced rollout?*

**Read-only.** This skill describes the order; it never edits code, writes or runs migration/backfill
scripts, or deploys. When it isn't sure a command is correct, it marks it `# verify` rather than inventing one.

## Scope detection

Resolve what to analyze, in this order:

1. `args` names files or a ref range (`HEAD~3..HEAD`, `origin/main...HEAD`) → use that.
2. A PR is in context (number/URL, or current branch has one) → diff the PR against its base.
3. Otherwise → uncommitted work: `git diff HEAD` (fall back to `git diff --cached`, then last commit `git show HEAD`).

Report the resolved scope in one line before analyzing.

```bash
git diff HEAD                      # default scope
git diff origin/main...HEAD        # branch vs base
```

## Hazard catalog

Scan the diff for each of these. Each hazard carries an ordering implication — that implication is the
whole point of flagging it.

| Hazard | What to look for | Ordering implication |
|---|---|---|
| **DB schema / migration** | column/table `DROP` or `RENAME`, `ADD COLUMN ... NOT NULL` without default, type narrowing, new `UNIQUE` on existing data, lock-heavy index builds | expand → migrate → backfill → switch reads → (later PR) contract. Never drop a column the running code still reads. |
| **API / contract** | removed/renamed field, param, or endpoint still consumed by older clients; response-shape change; GraphQL/proto/OpenAPI schema edits | deprecate-then-remove; deploy the side that *tolerates both* first (usually consumer-tolerant before producer-strict). |
| **Message / event / queue schema** | Kafka/PubSub topic or payload shape change, new required field on an event | dual-write / dual-read window; deploy consumers that accept old+new before producers emit new. |
| **Config / env / secret** | new **required** env var, secret, or config key the new code reads at boot | set config in the target env **before** the code that needs it deploys. Missing → crash loop. |
| **Feature flag / kill switch** | behavior gated behind a flag | ship dark (flag off), deploy, then ramp the flag separately. |
| **Data backfill / one-off script** | a script that must populate/transform data | sequence relative to deploy (before? after migration? before reads switch?). |
| **Serialization / cache key / format** | cache value shape change, serializer version bump, changed cache key | versioned keys or invalidation; old and new instances must not fight over one key. |
| **Cross-service removal** | deleting code/endpoint other services or repos still call | coordinate across repos; remove callers first, provider last. |

If none of these appear and the change has no public/contract/schema/config surface (isolated new
component, internal refactor with stable signatures, docs, tests) → **skip**: emit the `✅` line and stop.

## Output

Lead with a one-line verdict:

- `✅ No special deploy ordering needed` — single deploy is safe.
- `⚠️ Requires ordered rollout` — followed by the runbook.

When ordered rollout is required, emit a **numbered runbook**. Order steps so that at every point the
deployed system is internally consistent (no instance reads what doesn't exist yet, no instance writes
what readers can't parse):

```
## Rollout / Deploy order

1. <step> — <what> · <why> · `command-or-script  # verify`
2. ...
N. Follow-up PR: <contract step deferred to keep this deploy safe>

Rollback: <how to reverse, and which steps are point-of-no-return (e.g. destructive migration)>
```

Then a short evidence list so the user can audit the call:

```
What I detected
- <hazard> — file:line — <one-line note>
```

Keep it tight. Don't pad safe changes; don't list a hazard you can't point to a line for.

## Integration contract (branch-pr / go)

When invoked by `gbase:branch-pr` or `gbase:go` on the change being shipped:

- Return the `## Rollout / Deploy order` block verbatim so the caller can drop it into the PR body —
  **only** when the verdict is `⚠️`. On `✅`, return the single verdict line and no section.
- Also return a one-line summary the caller surfaces to the user, e.g.
  `⚠️ This change needs a sequenced rollout (migration before deploy) — see the Rollout section in the PR.`

The caller owns the PR; this skill only hands back text.

## Boundaries

- **Read-only.** No `Edit`/`Write`; never run migrations, backfills, or deploys — describe the order only.
- Mark any command you can't verify against the repo with `# verify`; never fabricate exact commands,
  table names, or env keys.
- Cross-service / multi-repo ordering can't be fully proven from one diff — state the assumption
  explicitly. In interactive use, ask via `AskUserQuestion` when the safe order genuinely depends on
  info not in the diff (e.g. "are there old clients still calling `/v1/users`?").

## Usage

```
/gbase:compat-check                         # uncommitted diff
/gbase:compat-check origin/main...HEAD      # branch vs base
/gbase:compat-check src/db/ src/api/        # specific paths
```
