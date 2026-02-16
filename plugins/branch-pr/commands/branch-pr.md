---
description: "Automate branch creation, commit grouping, and PR generation from current changes"
allowed-tools: ["Bash", "Read", "Glob", "Grep", "AskUserQuestion"]
---

# /branch-pr Command

Analyzes current changes, creates a branch, auto-groups files into logical commits, and generates a PR.

## Safety Rules (Mandatory)

**Strictly Prohibited Commands:**
- `git reset --hard`
- `git checkout .`
- `git clean -f`
- `git stash drop` (unless explicitly requested by user)
- `git push --force`

**Required Practices:**
- Request user confirmation at every step
- Never use destructive commands
- On error, stop immediately and provide recovery instructions

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

### Step 2: Create Backup

Always create a backup before starting:

```bash
# Create a stash backup with timestamp
git stash push -m "branch-pr-backup-$(date +%Y%m%d-%H%M%S)" --include-untracked
```

Notify the user after backup creation:
- Confirm backup was created
- Provide recovery instructions: `git stash pop` or `git stash list`

Then restore from stash:
```bash
git stash pop
```

### Step 3: Suggest Branch Name

Suggest a branch name based on the change analysis:
- `feat/feature-name` - New feature
- `fix/bug-name` - Bug fix
- `refactor/area` - Refactoring
- `docs/doc-name` - Documentation changes
- `chore/task-name` - Miscellaneous tasks

Ask the user to confirm or modify the suggested branch name (use AskUserQuestion).

### Step 4: Create Branch

```bash
# Create and switch to new branch
git checkout -b <branch-name>
```

### Step 5: Propose Commit Grouping

Group changed files logically and propose commits:

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

Ask the user to confirm or modify the grouping and commit messages.

### Step 6: Execute Commits

Commit sequentially for each approved group:

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

```bash
gh pr create --title "<PR title>" --body "$(cat <<'EOF'
## Summary
<bullet point summary of changes>

## Changes
<changes organized by commit>

## Test plan
- [ ] Test items

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Return the PR URL to the user.

### Step 9: Cleanup (Optional)

Ask the user whether to clean up the backup:
- "Would you like to delete the backup stash?"
- If yes: `git stash drop stash@{0}` (only the specific backup)
- If no: Provide instructions on how to view backups

## Error Handling

On any error:
1. Stop all operations immediately
2. Print current state (`git status`)
3. Provide recovery instructions:
   - "To restore from backup: `git stash pop`"
   - "To delete the branch: `git checkout main && git branch -D <branch-name>`"

## Usage Example

```
User: /branch-pr

Claude: Analyzing changes...

[Analysis Result]
- Modified: src/db/schema.ts, src/app/api/users/route.ts
- Added: src/components/UserProfile.tsx

Suggested branch name: feat/user-profile

[Proposed Commit Grouping]
1. feat(db): add user profile fields
2. feat(api): add user profile endpoint
3. feat(ui): add UserProfile component

Proceed with this plan?
```
