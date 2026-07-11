---
description: "Automate branch creation, commit grouping, and PR generation from current changes"
allowed-tools: ["Bash", "Read", "Glob", "Grep", "AskUserQuestion", "Skill"]
---

# /branch-pr Command

Analyzes current changes, creates a branch, auto-groups files into logical commits, and generates a PR.

**Runs fully autonomously by default.** Invoking `/branch-pr` is itself the go-ahead to decide the branch
name, group commits, push, and open the PR without step-by-step confirmation. Only pause when a case in
[Ask only when necessary](#ask-only-when-necessary) genuinely applies. Report what you decided as you go;
don't ask the user to ratify routine choices.

## Safety Rules (Mandatory)

**Strictly Prohibited Commands:**
- `git reset --hard`
- `git checkout .`
- `git clean -f`
- `git stash drop` (unless explicitly requested by user)
- `git push --force` (`--force-with-lease` is fine for legitimate rebases)

**Required Practices:**
- Operate autonomously — decide branch name, commit grouping, and PR body yourself
- Stop only for the [Ask only when necessary](#ask-only-when-necessary) cases
- Never use destructive commands
- On error, stop immediately and provide recovery instructions

## Ask only when necessary

These are the *only* cases that interrupt the autonomous flow (use `AskUserQuestion`). Everything else
proceeds without asking:

- **Secrets/credentials in the diff** — `.env*`, private keys, tokens, or other secret-looking values.
  Stop; never auto-commit them. Ask how to proceed (e.g. unstage, add to `.gitignore`).
- **Unrelated pre-existing changes** — the working tree mixes in WIP clearly unrelated to the intended
  change. Ask whether to include it or leave it behind.
- **Ambiguous PR split** — the changes span clearly separate features and it's unclear whether they
  belong in one PR or several. Ask: one PR vs split.
- **On a diverged non-default branch** — already on a feature branch with its own history. Ask: new
  branch off the default, or keep committing on the current one.
- **Remote ambiguity** — no remote, multiple remotes, or the target branch already exists on the remote.
  Ask which remote / how to proceed.

When none apply, run end to end silently except for progress reporting.

## Execution Steps

### Step 1: Status Analysis (Read-Only)

```bash
# Check current changes
git status

# View staged/unstaged change details
git diff HEAD

# Check current branch
git branch --show-current

# View recent commits for context
git log --oneline -5
```

Analyze changed files and compile the following:
- List of changed files
- Change type for each file (modified/added/deleted)
- Logical grouping of files (by directory/feature)

**Nothing to ship** (clean tree — no modified, staged, or untracked files) → stop here and tell the user.
Do not proceed to Step 2: the backup `git stash push` would create nothing, and the `git stash apply`
that follows would resurrect whatever unrelated stash the user already had at `stash@{0}`.

### Step 2: Create Backup

Always create a backup before starting:

```bash
# Create a stash backup with timestamp
git stash push -m "branch-pr-backup-$(date +%Y%m%d-%H%M%S)" --include-untracked
```

Confirm the backup was actually created, then reapply the changes while **keeping** the stash as a
persistent backup (`apply`, not `pop`):

```bash
git stash list | head -1   # must show the branch-pr-backup message you just wrote
git stash apply
```

If `git stash push` printed `No local changes to save` (Step 1 should have already stopped you), **do not
run `git stash apply`** — with no fresh backup on the stack it would apply an unrelated, pre-existing stash.

The stash stays in the list (as `stash@{0}`) so it remains a real recovery point through the rest of the
run. Recover anytime with `git stash apply` / inspect with `git stash list`.

### Step 3: Decide Branch Name

Pick a branch name from the change analysis — no confirmation needed. Report it in one line, then continue.

- `feat/feature-name` - New feature
- `fix/bug-name` - Bug fix
- `refactor/area` - Refactoring
- `docs/doc-name` - Documentation changes
- `chore/task-name` - Miscellaneous tasks

### Step 4: Create Branch

```bash
# Create and switch to new branch
git checkout -b <branch-name>
```

### Step 5: Group Commits

Group changed files logically and commit them — decide the grouping and messages yourself, no confirmation
needed. Report each group as you commit it.

**Grouping Criteria:**
1. By directory/layer (db, api, components, etc.)
2. By feature relevance
3. By change type (schema, migration, test, etc.)

For each group, provide:
- List of included files
- Suggested commit message (conventional commits format)

Example:
```
Group 1: Database changes
  - src/db/schema.ts
  - db/migrations/0001_xxx.sql
  → "feat(db): add user preferences table"

Group 2: API endpoints
  - src/app/api/preferences/route.ts
  → "feat(api): add preferences endpoint"

Group 3: UI components
  - src/components/PreferencesForm.tsx
  - src/app/settings/page.tsx
  → "feat(ui): add preferences settings page"
```

### Step 6: Execute Commits

Commit sequentially for each group:

```bash
# Group 1
git add <file1> <file2> ...
git commit -m "$(cat <<'EOF'
commit message

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Group 2 ...
```

Run `git status` after each commit to verify state.

### Step 7: Push

```bash
# Push to remote with upstream tracking
git push -u origin <branch-name>
```

### Step 8: Create PR

First, check backward-compatibility / deploy ordering. Invoke the `compat-check` skill on the pushed range:

```
Skill(skill: "gbase:compat-check", args: "origin/<default-branch>...HEAD")
```

- If it returns `⚠️ Requires ordered rollout`, inject its `## Rollout / Deploy order` block into the PR
  body (below) and print its one-line summary to the user as a heads-up.
- If it returns `✅`, omit the section entirely and say nothing extra.

Then create the PR. Add `--draft` to `gh pr create` when the user or `gbase:go` passed `--draft` —
`gbase:monitor` flips it to ready once CI is green and its self-review is resolved.

```bash
gh pr create --title "<PR title>" --body "$(cat <<'EOF'
## Summary
<bullet point summary of changes>

## Changes
<changes organized by commit>

<!-- ## Rollout / Deploy order  ← only when compat-check returned ⚠️ -->

## Test plan
- [ ] Test items

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Return the PR URL to the user.

### Step 9: Cleanup

Don't ask. Leave the backup stash in place and print one line so the user can drop it themselves later:
- "Backup stash left at `stash@{0}` — `git stash drop stash@{0}` to remove, `git stash list` to view."

## Error Handling

On any error:
1. Stop all operations immediately
2. Print current state (`git status`)
3. Provide recovery instructions:
   - "To restore from backup: `git stash apply stash@{0}` (apply, not pop — keep the backup for another try)"
   - "To delete the branch: `git checkout main && git branch -D <branch-name>`"

## Usage Example

```
User: /branch-pr

Claude: Analyzing changes…
  Modified: src/db/schema.ts, src/app/api/users/route.ts
  Added:    src/components/UserProfile.tsx

Branch: feat/user-profile
Committing:
  ✓ feat(db): add user profile fields
  ✓ feat(api): add user profile endpoint
  ✓ feat(ui): add UserProfile component
Pushed feat/user-profile → origin.

compat-check: ⚠️ schema.ts adds a NOT NULL column — needs migrate-before-deploy.
  Added a "Rollout / Deploy order" section to the PR.

PR opened: https://github.com/owner/repo/pull/142
Backup stash left at stash@{0} — `git stash drop stash@{0}` to remove.
```

No "proceed?" prompt — it only stops for the [Ask only when necessary](#ask-only-when-necessary) cases
(e.g. a secret in the diff, unrelated WIP, an ambiguous PR split).
