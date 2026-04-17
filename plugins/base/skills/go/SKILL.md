---
name: go
description: "Finish code changes in one shot — run the bundled /simplify skill on the current diff, then run /gbase:branch-pr end-to-end. Invoke manually with /gbase:go; do not trigger automatically."
disable-model-invocation: true
allowed-tools: Bash Read Glob Grep AskUserQuestion Skill Edit Write
---

# /gbase:go

Wraps up a working session by running **simplify** on recent code, then **branch-pr** to ship it. The two steps run back-to-back without an extra confirmation between them — `branch-pr`'s own step-by-step confirmations still apply.

This skill has `disable-model-invocation: true`: only the user can trigger it via `/gbase:go`, never the model on its own.

## Flow

1. **Simplify** — invoke the bundled `simplify` skill (Claude Code's official refactor pass) on the recently changed code.
2. **Branch & PR** — invoke the `gbase:branch-pr` skill to back up, branch, group commits, push, and open a PR.

## Execution

### Step 1 — Detect scope

Run:

```bash
git status --short
git diff HEAD --stat
git log --oneline -1
```

Decide:

- **Uncommitted changes present** → simplify targets those files; branch-pr runs afterward.
- **Clean working tree** → simplify targets the most recent commit (`git show HEAD --name-only`); **skip** branch-pr and tell the user there's nothing to PR.

Report the detected scope to the user in one line, then proceed without waiting.

### Step 2 — Invoke simplify

Use the `Skill` tool:

```
Skill(skill: "simplify", args: "<list of in-scope files>")
```

If the `simplify` skill supports free-form args, pass the file list; otherwise just invoke it and rely on its own "recently modified" detection. Wait for it to finish. Summarize what it changed in one or two sentences.

### Step 3 — Invoke branch-pr

If Step 1 found uncommitted changes — or if simplify introduced new ones — immediately invoke:

```
Skill(skill: "gbase:branch-pr")
```

That skill owns the rest: status analysis, backup stash, branch suggestion (confirmed with `AskUserQuestion`), branch creation, commit grouping (confirmed with `AskUserQuestion`), sequential commits, `git push -u origin`, `gh pr create`, and optional backup cleanup.

All safety rules from `gbase:branch-pr` apply unchanged:

- Prohibited: `git reset --hard`, `git checkout .`, `git clean -f`, `git push --force`, `git stash drop` (unless the user explicitly asks).
- Required: confirm at each step, stop immediately on error, surface recovery instructions.

If Step 1 found no changes and simplify also produced no edits, stop after Step 2 and inform the user.

## Error handling

- **Simplify produces no changes, tree was already clean** → stop, inform the user.
- **Simplify fails** → surface the error; ask the user whether to continue to branch-pr with pre-existing changes or abort.
- **Branch-pr fails at any step** → stop, print `git status`, give recovery instructions:
  - Restore from backup stash: `git stash pop`
  - Delete the created branch: `git checkout main && git branch -D <branch-name>`

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

Running /simplify on these files…
[simplify makes 2 refactors in UserProfile.tsx]

Simplify done. Proceeding to /gbase:branch-pr.
Suggested branch: feat/user-profile — confirm?
…
```
