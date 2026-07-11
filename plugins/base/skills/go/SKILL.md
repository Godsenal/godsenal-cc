---
name: go
description: "Finish code changes in one shot — run the /gbase:polish skill (deslop + structural pass) on the current diff, run /gbase:branch-pr end-to-end, then hand off to /gbase:monitor to watch CI and reviews until merge; monitor also self-reviews the fresh PR (built-in code-review) after it opens, so review never slows the path to PR. Invoke manually with /gbase:go, or let the model auto-trigger it when the user signals a change is done and wants it shipped."
allowed-tools: Bash Read Glob Grep AskUserQuestion Skill Edit Write
---

# /gbase:go

Wraps up a working session by running **polish** on recent code (deslop + ambitious structural pass), **branch-pr** to ship it, and **monitor** to babysit CI + reviews until merge. The three steps run back-to-back without extra confirmation between them — each sub-skill's own confirmations still apply.

Model-invocable: the user can trigger it via `/gbase:go`, and the model may auto-trigger it when the user signals a chunk of work is finished and wants it shipped (polish → PR → monitor). Because each sub-step (`branch-pr` push/PR, `monitor` auto-fixes) carries its own consent and safety rules, those still gate the side effects — `go` itself just sequences them.

## Flow

1. **Detect scope** — decide whether polish targets the uncommitted diff or the latest commit.
2. **Polish** — invoke the `gbase:polish` skill (deslop pass → structural pass) on the in-scope code.
3. **Branch & PR** — invoke the `gbase:branch-pr` skill to back up, branch, group commits, push, and open a PR.
4. **Monitor** — invoke the `gbase:monitor` skill to watch CI, auto-fix clear failures, and address review comments until the PR is merged or closed. Monitor also runs one self-review of the fresh PR (built-in `code-review`) in parallel with the watch, so review adds nothing to the time-to-PR.

## Execution

### Step 1 — Detect scope

Run:

```bash
git status --short
git diff HEAD --stat
git log --oneline -1
```

Decide:

- **Uncommitted changes present** → polish targets those files; branch-pr runs afterward.
- **Clean working tree** → polish targets the most recent commit (`git show HEAD --name-only`). If polish introduces new edits, branch-pr still runs on those; if it doesn't, skip branch-pr and tell the user there's nothing to PR.

Report the detected scope to the user in one line, then proceed without waiting.

### Step 2 — Invoke polish

Use the `Skill` tool:

```
Skill(skill: "gbase:polish", args: "<list of in-scope files>")
```

The skill runs a deslop pass (mechanical AI-cruft removal) then a structural pass (ambitious behavior-preserving restructuring). Larger structural moves prompt the user via `AskUserQuestion` before touching code; smaller ones apply directly. Wait for it to finish. Summarize what landed in one or two sentences.

### Step 3 — Invoke branch-pr

If Step 1 found uncommitted changes — or if polish introduced new ones — immediately invoke:

```
Skill(skill: "gbase:branch-pr")
```

That skill owns the rest and runs **fully autonomously** — it decides the branch name, commit grouping, and PR body itself, pushes, and opens the PR without step-by-step confirmation, stopping only for its narrow "ask only when necessary" cases (secret in the diff, unrelated WIP, ambiguous PR split, remote ambiguity). As part of PR creation it invokes `gbase:compat-check` on the change; if a sequenced rollout is needed (migration-before-deploy, new required env, etc.), it injects a `## Rollout / Deploy order` section into the PR body and flags it to you.

All safety rules from `gbase:branch-pr` apply unchanged — `go` is a pure wrapper.

If Step 1 found no changes and polish also produced no edits, stop after Step 2 and inform the user.

### Step 4 — Invoke monitor

Immediately after `branch-pr` returns successfully with a PR URL, chain into:

```
Skill(skill: "gbase:monitor")
```

That skill resolves the PR for the current branch, sweeps current CI + reviews, and starts a persistent `Monitor` that runs until the PR is merged or closed. It auto-fixes clear CI failures (lint, format, type, missing imports) and applies clearly-required review comments (suggested diff blocks, typos, dead-code removal); ambiguous items get surfaced with `AskUserQuestion`. It then runs one self-review of the PR (built-in `code-review`) while the watch runs: clear findings are auto-fixed in their own commits, everything else comes back as an organized report — nothing is posted to GitHub. Pass `--no-review` to skip it, or `--draft` to have branch-pr open a draft PR that monitor flips to ready once CI is green and the self-review is resolved (both flags pass through).

If `branch-pr` was skipped (no changes), skip this step too.

If the user wants to ship without ongoing monitoring, they can stop the Monitor with `TaskStop` mid-flight; `branch-pr`'s work is already on the remote.

## Error handling

- **Polish produces no changes, tree was already clean** → stop, inform the user.
- **Polish fails** → surface the error; ask the user whether to continue to branch-pr with pre-existing changes or abort.
- **Branch-pr fails at any step** → stop, print `git status`, give recovery instructions:
  - Restore from backup stash: `git stash apply stash@{0}` (apply, not pop — keep the backup)
  - Delete the created branch: `git checkout main && git branch -D <branch-name>`
- **Monitor fails to start** (no `gh` auth, no PR resolvable, etc.) → surface the error and stop; `branch-pr`'s output (branch + PR) is unaffected.

## Usage

```
/gbase:go               # polish → PR → monitor (+ post-PR self-review)
/gbase:go --draft       # open a draft PR; monitor flips it to ready when CI green + self-review resolved
/gbase:go --no-review   # skip the post-PR self-review
```

Typical session:

```
User: /gbase:go

Claude: Detected 4 uncommitted files:
  M  src/db/schema.ts
  M  src/app/api/users/route.ts
  A  src/components/UserProfile.tsx
  A  src/components/UserProfile.test.tsx

Running /gbase:polish on these files…
[deslop strips 3 redundant comments + one defensive try/catch in UserProfile.tsx]
[structural pass inlines a single-caller helper in route.ts]

Polish done. Proceeding to /gbase:branch-pr.
Branch: feat/user-profile → committed, pushed (no confirmation needed).
compat-check: ✅ no special deploy ordering.
[branch-pr opens PR #142]

Proceeding to /gbase:monitor for PR #142.
Subscribing to CI + reviews (auto-fixing clear failures; will ping on anything ambiguous).
Self-review (code-review): 2 findings — 1 auto-fixed (missing await, pushed in a1b2c3d), 1 needs your call.
```
