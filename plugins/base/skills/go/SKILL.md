---
name: go
description: "Finish code changes in one shot — run the bundled /code-review skill on the current diff, run /gbase:branch-pr end-to-end, then hand off to /gbase:monitor to watch CI and reviews until merge. Invoke manually with /gbase:go; do not trigger automatically."
disable-model-invocation: true
allowed-tools: Bash Read Glob Grep AskUserQuestion Skill Edit Write
---

# /gbase:go

Wraps up a working session by running **code-review** on recent code, **branch-pr** to ship it, and **monitor** to babysit CI + reviews until merge. The three steps run back-to-back without extra confirmation between them — each sub-skill's own confirmations still apply.

This skill has `disable-model-invocation: true`: only the user can trigger it via `/gbase:go`, never the model on its own.

## Flow

1. **Detect scope** — decide whether code-review targets the uncommitted diff or the latest commit.
2. **Code review** — invoke the bundled `code-review` skill (Claude Code's official review pass) on the in-scope code.
3. **Branch & PR** — invoke the `gbase:branch-pr` skill to back up, branch, group commits, push, and open a PR.
4. **Monitor** — invoke the `gbase:monitor` skill to watch CI, auto-fix clear failures, and address review comments until the PR is merged or closed.

## Execution

### Step 1 — Detect scope

Run:

```bash
git status --short
git diff HEAD --stat
git log --oneline -1
```

Decide:

- **Uncommitted changes present** → code-review targets those files; branch-pr runs afterward.
- **Clean working tree** → code-review targets the most recent commit (`git show HEAD --name-only`). If code-review introduces new edits, branch-pr still runs on those; if it doesn't, skip branch-pr and tell the user there's nothing to PR.

Report the detected scope to the user in one line, then proceed without waiting.

### Step 2 — Invoke code-review

Use the `Skill` tool:

```
Skill(skill: "code-review", args: "<list of in-scope files>")
```

If the `code-review` skill supports free-form args, pass the file list; otherwise just invoke it and rely on its own "recently modified" detection. Wait for it to finish. Summarize what it changed in one or two sentences.

### Step 3 — Invoke branch-pr

If Step 1 found uncommitted changes — or if code-review introduced new ones — immediately invoke:

```
Skill(skill: "gbase:branch-pr")
```

That skill owns the rest: status analysis, backup stash, branch suggestion (confirmed with `AskUserQuestion`), branch creation, commit grouping (confirmed with `AskUserQuestion`), sequential commits, `git push -u origin`, `gh pr create`, and optional backup cleanup.

All safety rules from `gbase:branch-pr` apply unchanged — `go` is a pure wrapper.

If Step 1 found no changes and code-review also produced no edits, stop after Step 2 and inform the user.

### Step 4 — Invoke monitor

Immediately after `branch-pr` returns successfully with a PR URL, chain into:

```
Skill(skill: "gbase:monitor")
```

That skill resolves the PR for the current branch, sweeps current CI + reviews, and starts a persistent `Monitor` that runs until the PR is merged or closed. It auto-fixes clear CI failures (lint, format, type, missing imports) and applies clearly-required review comments (suggested diff blocks, typos, dead-code removal); ambiguous items get surfaced with `AskUserQuestion`.

If `branch-pr` was skipped (no changes), skip this step too.

If the user wants to ship without ongoing monitoring, they can stop the Monitor with `TaskStop` mid-flight; `branch-pr`'s work is already on the remote.

## Error handling

- **Code-review produces no changes, tree was already clean** → stop, inform the user.
- **Code-review fails** → surface the error; ask the user whether to continue to branch-pr with pre-existing changes or abort.
- **Branch-pr fails at any step** → stop, print `git status`, give recovery instructions:
  - Restore from backup stash: `git stash pop`
  - Delete the created branch: `git checkout main && git branch -D <branch-name>`
- **Monitor fails to start** (no `gh` auth, no PR resolvable, etc.) → surface the error and stop; `branch-pr`'s output (branch + PR) is unaffected.

## Usage

```
/gbase:go
```

Typical session:

```
User: /gbase:go

Claude: Detected 4 uncommitted files:
  M  src/db/schema.ts
  M  src/app/api/users/route.ts
  A  src/components/UserProfile.tsx
  A  src/components/UserProfile.test.tsx

Running /code-review on these files…
[code-review makes 2 fixes in UserProfile.tsx]

Code-review done. Proceeding to /gbase:branch-pr.
Suggested branch: feat/user-profile — confirm?
…
[branch-pr opens PR #142]

Proceeding to /gbase:monitor for PR #142.
Subscribing to CI + reviews (auto-fixing clear failures; will ping on anything ambiguous).
```
