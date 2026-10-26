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

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

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

Under `AGENT_HEADLESS=1` (check `printenv AGENT_HEADLESS` before asking) these cases don't ask: follow [headless.md](../references/headless.md). A secret is never committed — leave it out and record it.

## Local mode

When the args start with `Ship-owner: orchestrator; PR-body-file: <path>` (`gbase:go` under `AGENT_SHIP_OWNER=orchestrator`), another program pushes the branch and opens the PR. This run prepares both and touches no remote:

- **Branch:** commit on the current branch; Steps 3–4 run only when it is the default branch. The caller owns its branch, so the diverged-branch and remote cases aren't questions here.
- **Already committed:** a clean tree with commits ahead of the base skips Steps 2–6 instead of stopping.
- **Remote untouched:** skip Step 7, `gh pr create`, and the `gbase-assets` upload; embed each screenshot as `![<label>](<absolute local path>)` so the caller can upload it and rewrite the link.
- **Body:** Step 8 as written. Invoke `gbase:compat-check` there even for a change that looks additive; it is the draft's only deploy-order review. Run it on `<base>...HEAD` (base = `origin/<default>` when it exists, else the local default branch). Write the title as line 1, an empty line 2, then the body, to the path (`mkdir -p` its directory; overwrite).
- **Report** the lines the caller greps: `ship: local <branch> @<short-sha> — <n> commits, not pushed` and `PR 본문 초안: <path>` ([format](../references/orchestrator.md#report-lines)). Not pushing is the contract, not a decision: no `결정 필요:` line for the push or the PR.

## Execution Steps

### Step 1: Status Analysis (Read-Only)

First, unwrap `gbase:pause` checkpoints so the analysis below sees their changes. A pause commit has a `wip:` subject
**and** an `Intent:` body line; a hand-written `wip:` commit without it is the user's and stays. Count the unpushed
pause commits at the tip, keep their bodies (the resume notes — read them for the PR's Why), then soft-reset:

```bash
n=0
while git log -1 --format=%s "HEAD~$n" 2>/dev/null | grep -q '^wip:' \
  && git log -1 --format=%b "HEAD~$n" | grep -q '^Intent:' \
  && [ -z "$(git branch -r --contains "HEAD~$n")" ]; do n=$((n+1)); done
[ "$n" -gt 0 ] && git log -"$n" --format=%B && git reset --soft "HEAD~$n"
```

A pushed pause commit is never reset. Then analyze:

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

**Nothing to ship** (clean tree — no modified, staged, or untracked files) → stop here and tell the user;
in [local mode](#local-mode), only when no commits are ahead of the base either.
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

<attribution trailer the session specifies, if any>
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

Classify the risk, unless the caller (e.g. `gbase:go`) passed a `Risk:` line — the tier is set from
the change, not the author:

- `high` — touches a path `REVIEW.md` marks always-high (without one: auth, payments/billing, migrations,
  CI/release workflows, app config like `app.json`/`eas.json`/`Info.plist`), or compat-check returned ⚠️
- `low` — docs, copy, tests, or an additive change behind a flag, and nothing above
- `medium` — everything else

If the repo has its own PR template (`.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`,
or `docs/pull_request_template.md`), fill that template's sections instead of the one below, and add whichever of
`Review focus` (with its risk line and folded list) and `Evidence` it lacks: `Review focus` right under its first
section, `Evidence` wherever it fits.

Then create the PR. Add `--draft` to `gh pr create` when the user or `gbase:go` passed `--draft` —
`gbase:monitor` flips it to ready once CI is green and its self-review is resolved.

Run the drafted title and body through `gbase:unslop` before creating the PR.

The body is a briefing for a reviewer who has the diff. **The reviewer reads `Review focus` first and may
stop there**, so everything a person has to judge goes in it and nowhere else; the sections below it are
reference:

```bash
gh pr create --title "<PR title>" --body "$(cat <<'EOF'
## Why
<exactly one sentence: the problem, and what becomes possible once this ships>

## Review focus
> [!IMPORTANT]
> **사람이 볼 곳 <N>건**
> 1. **<the question, as one short bold line>** (결정)
>    `path:line` · <why no check can answer it, a few words>
> 2. **<what to look at and what "right" looks like>** (확인)
>    <where: a screenshot below, `path:line`, a device>
> 3. **<the failure, as a question>** (보류 · medium)
>    `path:line` · <failure scenario>

**위험도** <low / medium / high> (<the path or hazard that set it>) · <two-way / one-way> · <how to undo: revert the squash commit, plus anything left behind>

<details><summary>보류한 리뷰 지적 <K>건 · low 또는 기존 코드</summary>

- `path:line` <finding, one line> (low · 기존 코드)
</details>

<!-- N = 0: `> [!NOTE]` and one line: **사람이 판단할 곳 없음.** <why the checks and the Evidence cover it>.
     K = 0: drop the details block. -->

## Change outline
<one small view per concern, each under a bold one-line lead (e.g. **새 스킬**, **저장 흐름**, **스키마**):
a table for 3+ parallel items, otherwise the form from the table below that fits the concern. Not a
per-commit or per-file changelog: the Commits tab already is one>

## Evidence
<before → after first, in the form that shows this change best (table below); a `| | Before | After |`
table when there are two or more. Then the checks already run (the `Verification:` lines the caller
passed), one `- [x]` line each with what was observed>

<!-- ## Rollout / Deploy order  ← only when compat-check returned ⚠️ -->

## Notes
<only what a reviewer would trip on that isn't a Review focus item (a deliberate omission, an out-of-scope
find). Usually empty: drop the section>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Review focus** — what a person must judge because no check here can. Before writing an item, name what the
checks would miss; if you can't, it isn't an item. Most-severe first, at most five; more than that means
the PR should be split, so say so as item 1. Each item is a bold line a reviewer can answer, its kind in parentheses after the bold, and one plain line
under it for where and why. Keep code spans out of the bold part:

- `(결정)` a product or design call: copy, a tradeoff the author picked, a behavior change someone may not want, a pattern other code will copy.
- `(확인)` evidence only a person can judge (how a screen looks, real data, a device), any surface the run couldn't reach (`behavior: skip`), or a `high`-tier path from the risk rule above — point at the exact lines.
- `(보류 · <severity>)` a finding from the caller's `Deferred:` line marked `introduced` and rated `medium` or above. The rest (`low`, or `pre-existing`) go in the folded details block, marked `기존 코드` when pre-existing so they don't read as the author's fault — they never count toward N.

The alert renders as a colored box, so it stays the one thing that stands out; don't add other alert boxes elsewhere in the body.

**Two-way / one-way:** two-way when reverting the squash commit restores the old behavior. One-way when something
outlives the revert — a dropped column or rewritten data, a sent notification or email, a store
submission, a removed public API; take the point of no return from compat-check's Rollback line, and add
a `(확인)` item for it. If `gbase:blast-radius` ran, its confirmed risks become `(확인)` items.
The risk line informs the reviewer; it never blocks the PR.

**Readable in a minute.** The body before `## Change outline` fits on one screen. Every section is tables
and one-line bullets, no paragraph over two lines. A Change outline over ~25 lines or four groups, and any
long table or command output, goes inside `<details><summary>…</summary>` with its lead line outside; if
it still doesn't fit, the PR should be split.

**Pick the form per change** — for each Outline view and each Evidence pair, the one a reviewer grasps fastest:

| What changed | Show it as |
|---|---|
| How a screen looks (UI, layout, copy) | before/after screenshots side by side |
| Interaction or animation | a short GIF |
| A flow across components or services | a `mermaid` sequence diagram (GitHub renders it) |
| Logic or an algorithm | a pseudocode `diff`, plus the test that failed and now passes |
| An API, event, or RPC contract | a request/response JSON `diff` |
| Schema | a table `diff`, plus what the migration does |
| Performance | one number with its unit, before → after |
| A refactor | a file-tree `diff`, plus "the same tests pass unchanged" |
| CLI or script behavior | terminal output before/after |

**Screenshots and GIFs.** A change to what a user sees ships with the image in the body. A local path left
in a pushed PR body (`~/…/shots/after.png`) is not evidence, because the reviewer can't open it. Take them from the run's
captures: the `verify-*` artifacts (`artifacts/verify/<feature>/`, gitignored) or the evidence dir in the
`behavior:` lines. "After" is always available; include "before" only when the run already captured it
(e.g. it reproduced the bug first) — don't relaunch the old build just for a picture. When the run took no
screenshot of a UI change, take one of the after state now if the app is already running; otherwise make
it a `(확인)` item. A GIF needs `ffmpeg` to convert a recording (`xcrun simctl io booted recordVideo`,
Playwright video); without it, use two or three stills.
`gh` can't attach images to a PR body, so upload them to the `gbase-assets` branch with the contents API —
never commit them to the PR branch, and touch nothing in the working tree:

```bash
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
gh api "repos/$repo/git/ref/heads/gbase-assets" >/dev/null 2>&1 || \
  gh api "repos/$repo/git/refs" -f ref=refs/heads/gbase-assets -f sha="$(git rev-list --max-parents=0 HEAD | tail -1)"
# body via stdin — a screenshot's base64 can exceed the argument-length limit
{ printf '{"branch":"gbase-assets","message":"assets: <branch-name>/<file>","content":"'
  base64 < <local file> | tr -d '\n'; printf '"}'; } |
  gh api -X PUT "repos/$repo/contents/<branch-name>/<file>" --input -
# embed: ![after](https://github.com/<repo>/raw/gbase-assets/<branch-name>/<file>)
```

On a public repo those images are public — only upload screens with seeded demo data, never real user data.

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
