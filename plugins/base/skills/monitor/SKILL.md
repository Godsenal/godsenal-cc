---
name: monitor
description: "Watch a PR until merge/close — auto-fix clear CI failures, address clearly-needed review comments, resolve safe merge conflicts (lockfiles, pure additions), and run /simplify on every non-trivial auto-edit before committing. Ask on ambiguous ones. Invoke manually with /gbase:monitor or chained from /gbase:go; do not trigger automatically."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Skill Monitor
---

# /gbase:monitor

Subscribes to the current branch's PR and keeps it moving. CI failures with an obvious cause (lint, format, type, missing import) get fixed and pushed automatically. Review comments that are clearly required (typo, suggested diff blocks, dead code the reviewer pointed at) get applied. Merge conflicts that are mechanically safe (lockfile regeneration, pure additions) get resolved. Anything subjective — architecture, behavior changes, semantic conflicts, design preference — gets surfaced to the user instead.

`disable-model-invocation: true`: only triggers via `/gbase:monitor` or as the tail of `/gbase:go`.

## Flow

1. **Resolve PR** — find the PR for the current branch.
2. **Initial pass** — sweep current CI state, existing review threads, and mergeability; handle what's actionable.
3. **Subscribe** — start a persistent `Monitor` that polls every 30s and emits one event per state change.
4. **React to events** — on each notification, classify (clear vs ambiguous) and act.
5. **Stop** — exit when the PR is `MERGED` or `CLOSED`.

## Safety rules (mandatory)

Inherit from `gbase:branch-pr`, with one carve-out for the conflict-resolution rebase:

- Prohibited: `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, `git stash drop` (unless user explicitly asks).
- **Allowed for conflict resolution only**: `git push --force-with-lease` (which aborts if the remote moved) and per-file `git checkout --ours <file>` / `--theirs <file>` for the cases listed in [Conflict classification](#conflict-classification-safe-vs-unsafe). Never use these as shortcuts on a semantic conflict.
- Each autonomous fix is its own commit with a clear message; for non-rebase work push with plain `git push`.
- Stop and surface on any push/merge error; never retry destructively.
- Always snapshot before a rebase (see the BACKUP_SHA pattern below). If conflict resolution feels unclear, `git rebase --abort` is the safe undo — use it freely.
- Never resolve a review thread without applying or explicitly declining it.
- Never re-request review or dismiss approvals on the user's behalf.

## Step 1 — Resolve PR

```bash
gh pr view --json number,url,state,headRefName,baseRefName,reviewDecision,statusCheckRollup,isDraft,mergeable,mergeStateStatus \
  -q '{number,url,state,branch:.headRefName,base:.baseRefName,review:.reviewDecision,draft:.isDraft,mergeable,mergeState:.mergeStateStatus}'
```

If no PR exists for the current branch, stop and tell the user.

If `state` is already `MERGED` or `CLOSED`, stop with a one-line summary.

Capture the PR number, the `OWNER/REPO` slug (from `gh repo view --json nameWithOwner -q .nameWithOwner`), and the base branch — pass these to every later command so the poll script is unambiguous.

If `mergeable` is `CONFLICTING` at this point, jump straight to [Conflict handling](#conflict-handling) before doing anything else; resolving a conflict can flip CI back to running, so we want to handle it first.

## Step 2 — Initial pass

### 2a. CI snapshot

```bash
gh pr checks <pr-number> --json name,bucket,link,state,workflow
```

`bucket` values: `pass`, `fail`, `pending`, `skipping`, `cancel`.

- All `pass`/`skipping` → note it and skip to 2b.
- Any `fail`/`cancel` → for each failing check, pull logs and classify (see [Classification](#classification-clear-vs-ambiguous)):
  ```bash
  gh run view <run-id> --log-failed
  ```
- Any `pending` → note it; the Monitor will catch the resolution.

### 2b. Review snapshot

```bash
# Inline review comments (per-file, with line + suggested diff if present)
gh api "repos/<owner>/<repo>/pulls/<pr-number>/comments" \
  --jq '.[] | {id, path, line, user: .user.login, body, in_reply_to_id}'

# Top-level reviews (APPROVED / CHANGES_REQUESTED / COMMENTED)
gh api "repos/<owner>/<repo>/pulls/<pr-number>/reviews" \
  --jq '.[] | {id, state, user: .user.login, body, submitted_at}'

# Conversation comments (issue-style)
gh api "repos/<owner>/<repo>/issues/<pr-number>/comments" \
  --jq '.[] | {id, user: .user.login, body, created_at}'
```

For each unresolved comment, classify and act (see below). Record the largest comment IDs seen — the Monitor script uses these as the watermark.

## Step 3 — Subscribe (persistent Monitor)

Use the `Monitor` tool with `persistent: true`. The script polls every 30s and emits one stdout line per state change.

```bash
Monitor(
  description: "PR #<number> CI + reviews",
  persistent: true,
  timeout_ms: 3600000,
  command: <<<bash-command-string — substitute the captured values for <owner>/<repo>, <pr-number>, and the watermarks before passing to Monitor>>>
  OWNER_REPO="<owner>/<repo>"
  PR=<pr-number>
  LAST_FAILS=""                       # space-joined "<name>|<link>" set
  LAST_OVERALL=""                     # "pass" | "mixed"
  LAST_COMMENT_ID=<largest-comment-id-from-Step-2b-or-0>
  LAST_REVIEW_ID=<largest-review-id-from-Step-2b-or-0>
  LAST_MERGEABLE=""

  while true; do
    # state + mergeable in a single call
    pv=$(gh pr view "$PR" --json state,mergeable -q '"\(.state)|\(.mergeable)"' 2>/dev/null || echo "|")
    state="${pv%|*}"; mergeable="${pv#*|}"

    if [ "$state" = "MERGED" ] || [ "$state" = "CLOSED" ]; then
      echo "PR_STATE:$state"; break
    fi

    if [ "$mergeable" != "$LAST_MERGEABLE" ]; then
      [ "$mergeable" = "CONFLICTING" ] && echo "MERGE_CONFLICT"
      [ "$mergeable" = "MERGEABLE" ] && [ "$LAST_MERGEABLE" = "CONFLICTING" ] && echo "MERGE_CLEAN"
      LAST_MERGEABLE="$mergeable"
    fi

    # CI: emit each NEWLY-failing check, plus a single CI_ALL_PASS on flip to green.
    # Watermark is the set of currently-failing checks, so re-emitting is suppressed
    # even when unrelated checks toggle in the same cycle.
    checks_json=$(gh pr checks "$PR" --json name,bucket,link 2>/dev/null || echo "[]")
    fails=$(echo "$checks_json" | jq -r \
      '[.[] | select(.bucket=="fail" or .bucket=="cancel") | "\(.name)|\(.link)"] | sort | join(" ")')
    overall=$(echo "$checks_json" | jq -r \
      'if length>0 and all(.[]; .bucket=="pass" or .bucket=="skipping") then "pass" else "mixed" end')

    if [ "$fails" != "$LAST_FAILS" ]; then
      for entry in $fails; do
        case " $LAST_FAILS " in *" $entry "*) ;; *) echo "CI_FAIL:$entry" ;; esac
      done
      LAST_FAILS="$fails"
    fi
    if [ "$overall" = "pass" ] && [ "$overall" != "$LAST_OVERALL" ]; then
      echo "CI_ALL_PASS"
    fi
    LAST_OVERALL="$overall"

    # Inline review comments since watermark.
    new_comment=$(gh api --paginate "repos/$OWNER_REPO/pulls/$PR/comments" 2>/dev/null \
      | jq -c "[.[] | select(.id > $LAST_COMMENT_ID)] | sort_by(.id)" 2>/dev/null || echo "[]")
    echo "$new_comment" | jq -r '.[] | "REVIEW_COMMENT:\(.id)|\(.user.login)|\(.path):\(.line)"'
    max_c=$(echo "$new_comment" | jq -r 'map(.id) | max // empty')
    [ -n "$max_c" ] && LAST_COMMENT_ID=$max_c

    # Top-level reviews since watermark.
    new_review=$(gh api --paginate "repos/$OWNER_REPO/pulls/$PR/reviews" 2>/dev/null \
      | jq -c "[.[] | select(.id > $LAST_REVIEW_ID)] | sort_by(.id)" 2>/dev/null || echo "[]")
    echo "$new_review" | jq -r '.[] | "REVIEW:\(.id)|\(.user.login)|\(.state)"'
    max_r=$(echo "$new_review" | jq -r 'map(.id) | max // empty')
    [ -n "$max_r" ] && LAST_REVIEW_ID=$max_r

    sleep 30
  done
)
```

The `<<<...>>>` line is illustrative — the actual `Monitor` tool call passes the whole script as the `command` string argument; substitute `<owner>`, `<repo>`, `<pr-number>`, and the two watermark seeds with the values captured in Step 1 / Step 2b before invoking.

**Event contract.** Bare events have no payload; events with `:` carry payload fields separated by `|`:

- `MERGE_CONFLICT` (bare) — `mergeable` flipped to `CONFLICTING`. Handle before anything else; CI runs on the merge commit and will keep failing while the conflict stands.
- `MERGE_CLEAN` (bare) — `mergeable` flipped back to `MERGEABLE` after a conflict.
- `CI_FAIL:<name>|<link>` — one per newly-failing check (suppressed on re-emit by the `LAST_FAILS` watermark).
- `CI_ALL_PASS` (bare) — emitted once on transition to all-green.
- `REVIEW_COMMENT:<id>|<author>|<file>:<line>` — one per new inline comment.
- `REVIEW:<id>|<author>|<state>` — one per new top-level review.
- `PR_STATE:MERGED` or `PR_STATE:CLOSED` — final event before the script exits.

When you act on an event, fetch its full body with `gh api repos/$OWNER_REPO/pulls/comments/<id>` (inline) or `gh api repos/$OWNER_REPO/pulls/<pr>/reviews/<id>` (top-level).

## Step 4 — React to events

### MERGE_CONFLICT handling

This runs **before** any CI fix on the same poll cycle — a conflict can mask CI signal.

```bash
# Snapshot the working tree before doing anything risky. `git stash create` produces
# a stash sha without modifying the working tree; `git stash store` records it under
# refs/stash so it survives a rebase. If there was nothing to stash, sha is empty —
# capture HEAD as the recovery point instead.
BACKUP_SHA=$(git stash create "monitor-conflict-backup-$(date +%s)" 2>/dev/null || true)
if [ -n "$BACKUP_SHA" ]; then
  git stash store -m "monitor-conflict-backup-$(date +%s)" "$BACKUP_SHA"
else
  BACKUP_SHA=$(git rev-parse HEAD)
fi

git fetch origin <base-branch>
git rebase origin/<base-branch>
```

The rebase will stop at the first conflict. For each conflicted file, run:

```bash
git status --porcelain | grep -E '^(UU|AA|DU|UD)'
```

Classify per [Conflict classification](#conflict-classification-safe-vs-unsafe):

- **Safe** → resolve, `git add <file>`, continue.
- **Unsafe** → run `git rebase --abort`, then if `BACKUP_SHA` is a real stash ref (look it up in `git stash list` by message), restore it with `git stash pop`; otherwise the abort already returns to `BACKUP_SHA`. Ask the user with `AskUserQuestion`. Do not leave the working tree in a half-resolved state.

After all conflicts are resolved:

```bash
git rebase --continue
# Run Post-fix simplify on any non-lockfile, non-whitespace-only files that were
# resolved by merging logic from both sides (skip pure lockfile regens). If
# simplify produces edits, amend them into the rebase head with `git add` +
# `git commit --amend --no-edit` before pushing — keeps the rebased commit clean.
git push --force-with-lease  # safe: refuses if remote moved
```

`--force-with-lease` is the **only** force-push variant allowed; it aborts if someone else pushed to the branch since you last pulled. Plain `--force` remains prohibited.

If `--force-with-lease` is rejected (remote moved), stop and surface — do not retry destructively.

After pushing, the Monitor will pick up the new merge state and the CI re-run on its next poll.

### Conflict classification: safe vs unsafe

**Resolve automatically** when the conflicted file matches one of these patterns:

- **Lockfiles** (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, `Gemfile.lock`, `poetry.lock`, `Cargo.lock`, `composer.lock`, `go.sum`):
  - Take the base side (`git checkout --theirs <lockfile>`), then regenerate from the lockfile-free manifest:
    - `package-lock.json` → `npm install`
    - `pnpm-lock.yaml` → `pnpm install`
    - `yarn.lock` → `yarn install`
    - `bun.lock` → `bun install`
    - `Cargo.lock` → `cargo build` (or `cargo update -p <pkg>` for a single dep)
    - `go.sum` → `go mod tidy`
    - `poetry.lock` → `poetry lock --no-update`
  - Then `git add <lockfile>` and continue.
- **Generated/build artefacts** that should never have been committed (`dist/`, `build/`, `*.min.js`, `*.map`) — take base side, then regenerate if a `build` script exists.
- **Pure-addition conflicts** where both sides added different content at the same location *and the additions are independent* (e.g., separate enum entries, separate imports, separate test cases). Keep both. Detect by reading the conflict markers:
  - The `<<<<<<<` block contains only added lines (no overlap with the `=======` block's removed context).
  - The two blocks don't reference the same identifier.
- **Whitespace-only conflicts** — rerun the project's formatter (`prettier --write`, `gofmt`, `cargo fmt`, etc.) on the file, then `git add`.

**Ask the user** for everything else, including:

- Same lines edited differently on both sides (semantic conflict).
- Migration/schema files (`db/migrations/`, `prisma/migrations/`, `*.sql`).
- Config files where merged values could change runtime behavior (`.env*`, `tsconfig.json`, `next.config.*`, `vite.config.*`, `tailwind.config.*`, CI yamls).
- Any file containing logic where the base side's change and the PR's change touch the same function/method/block.
- Renames or moves where the other side modified the file at the old path.
- Conflict markers spanning more than ~30 lines, regardless of pattern — too much surface area to judge mechanically.
- The PR base branch is itself diverged (rebase reports >5 commits to replay) — surface so the user can decide between rebase and merge.

When asking, include in `AskUserQuestion`:

- File path + conflict marker excerpt (the `<<<<<<<` / `=======` / `>>>>>>>` block, truncated to ~20 lines).
- 2–3 options (e.g., "keep PR side / keep base side / merge manually with my edits / abort rebase and surface for me later").

If the user picks "merge manually," abort the rebase, restore from the stash, and stop the auto-resolution flow — the user takes over from there.

### Post-fix simplify

Whenever monitor produces a code edit (CI fix, review comment application, or non-trivial conflict resolution), run the bundled `simplify` skill on the touched files **before** staging the commit:

```
Skill(skill: "simplify", args: "<space-separated touched files>")
```

This mirrors `/gbase:go`'s pre-PR pass — automated edits drift into duplication, dead branches, or stringly-typed values just like hand-written ones do. Folding simplify into the same commit (rather than a follow-up commit) keeps PR history clean.

**Skip simplify** when the edit is provably mechanical and re-running it would be a no-op:

- Lint/format auto-fix output (the formatter already canonicalised the file).
- Verbatim application of a fenced ` ```suggestion ` block — the reviewer asked for exactly that diff; "simplifying" it would surprise them.
- Lockfile regeneration (it's not code).
- Whitespace-only conflict resolution.

**Run simplify** for everything else: typecheck fixes that added/removed code, missing-import additions, review comments that introduced new logic, conflict resolutions that merged logic from both sides.

If simplify itself produces edits, fold them into the same `git add` + `git commit` as the original fix — one commit, not two.

### CI_FAIL handling

```bash
gh run view <run-id-from-link> --log-failed | tail -200
```

Classify per [Classification](#classification-clear-vs-ambiguous):

- **Clear** → fix in-place; run [Post-fix simplify](#post-fix-simplify) on the touched files (skip for pure lint/format auto-fix); commit; push.
- **Ambiguous** → `AskUserQuestion` with the failing check, the error excerpt, and 2–3 candidate fixes.

After pushing, do **not** manually re-poll — the Monitor will pick up the new run.

### REVIEW_COMMENT handling

Fetch body:

```bash
gh api "repos/<owner>/<repo>/pulls/comments/<id>"
```

If the body contains a fenced ` ```suggestion ` … ` ``` ` block (not just the word "suggestion" in prose), the reviewer literally proposed the diff — apply the contents verbatim to the indicated `path` and line range:

```bash
gh api "repos/<owner>/<repo>/pulls/<pr>/comments/<id>" \
  --jq '{path, line, body}' \
  # then apply the suggested code to the indicated path:line range
```

For non-suggestion comments, classify per [Classification](#classification-clear-vs-ambiguous).

After applying:

```bash
# Run Post-fix simplify on the touched files (skip if the edit was a verbatim
# `suggestion` block application — see Post-fix simplify section).
Skill(skill: "simplify", args: "<touched files>")

git add <files>
git commit -m "address review: <one-line summary>"
git push
```

Then post a reply (see [Always reply on the comment](#always-reply-on-the-comment)).

### Always reply on the comment

Every inline review comment monitor touches gets exactly one reply back, regardless of outcome — applied, declined, or deferred to the maintainer. Reviewers should never wonder whether their comment was seen.

```bash
gh api "repos/<owner>/<repo>/pulls/<pr>/comments/<id>/replies" \
  -X POST -f body="<one-line reply per the table below>"
```

| Outcome | Reply template |
|---|---|
| Applied (auto) | `Addressed in <short-sha>.` |
| Applied (after `AskUserQuestion` confirmed) | `Addressed in <short-sha>.` |
| Declined (user picked "skip" via `AskUserQuestion`) | `Discussed with the maintainer — keeping current approach. <one-line reason>` |
| Declined (clearly out of scope per Classification) | `Out of scope for this PR — tracking separately.` |
| Deferred (waiting on maintainer decision, no answer yet) | `Surfaced to the maintainer; will follow up here once decided.` |
| Question, not a request | `Answering inline: <one-line answer>` (or surface to maintainer if you don't know) |

Tone rules:

- One line. No apologies, no hedging, no "thanks for the feedback" filler.
- If declining, name the reason concretely (e.g., *"this path is only hit during migration, behavior change would break v1 callers"*) — never a vague *"we decided not to"*.
- Never reply twice to the same comment id. Before posting, scan the existing replies (`gh api repos/<owner>/<repo>/pulls/<pr>/comments` → filter where `in_reply_to_id == <id>` and `user.login == <bot/your account>`); if monitor already replied, skip.
- Never auto-resolve the review thread. Reviewers resolve their own threads.

### REVIEW handling

- `APPROVED` — log it for the user; no reply.
- `CHANGES_REQUESTED` — read the review body. Treat top-level summary points as a checklist; expand each against the inline comments already emitted. Each individual inline comment gets its own reply via [Always reply on the comment](#always-reply-on-the-comment). When *all* points in the review have been resolved (applied or declined), post a single summary comment on the PR so the reviewer doesn't have to crawl every thread:
  ```bash
  gh api "repos/<owner>/<repo>/issues/<pr>/comments" -X POST -f body="\
  @<reviewer> addressed your review:\n\
  - Applied: <bullet list of applied comment links>\n\
  - Declined: <bullet list with one-line reasons>\n\
  - Deferred: <bullet list with status>"
  ```
- `COMMENTED` — body may contain a summary; act on it the same way as inline comments. If the body itself contains a request not tied to a specific line (i.e., not also present as an inline comment), reply with a PR-level issue comment instead.

## Classification: clear vs ambiguous

**Apply automatically** when ALL of these hold:

- The change is mechanical: rename, formatting, lint/typecheck fix, unused-import/variable removal, missing-await, obvious typo, applying a `suggestion` block verbatim.
- The fix is local (one or two files, under ~20 lines of diff).
- No behavior change beyond what the reviewer explicitly named.
- No new dependency, no schema/migration change, no API contract change.
- The reviewer's intent is stated directly, not implied.

**Ask the user** when ANY of these hold:

- Architecture, abstraction, or design choice ("should this be a hook instead?").
- Test added or removed.
- Behavior change ("we should also handle X").
- Performance trade-off.
- Comment is a question ("why does this do X?") rather than a request.
- The reviewer hedges ("maybe", "consider", "could we...") — surface it, don't decide unilaterally.
- The fix would require changes in files the reviewer didn't reference.

When in doubt, ask. The cost of asking is one prompt; the cost of an unwanted change is a re-review cycle.

When asking, include in `AskUserQuestion`:

- Reviewer name + the comment body (one short quote).
- File:line.
- 2–3 concrete options (e.g., "apply X / counter-propose Y / leave a reply explaining Z / skip and surface later").

## Step 5 — Stop

When the Monitor emits `PR_STATE:MERGED` or `PR_STATE:CLOSED` it exits on its own. Print a one-line summary:

- CI failures auto-fixed.
- Review comments: applied / declined / deferred (the same three buckets that drove the replies).
- Merge conflicts resolved automatically vs aborted-and-surfaced.
- Final PR state and URL.

Then stop. Do not start a new Monitor.

## Error handling

- **`gh` auth missing** → stop, tell the user to run `gh auth login`.
- **No PR for branch** → stop, suggest `/gbase:branch-pr`.
- **Push rejected** (branch out of date) → `git pull --rebase`, then retry once. If conflicts surface, hand off to [MERGE_CONFLICT handling](#merge_conflict-handling). If still failing without conflicts, surface and stop.
- **Conflict during rebase** → use the classification flow above. Anything outside the "safe" list → `git rebase --abort`, restore the backup stash, ask the user.
- **`--force-with-lease` rejected** (remote moved during conflict resolution) → stop, do not retry; surface the rejection to the user.
- **Monitor script exits with non-zero** → print the last error line, ask the user whether to restart.
- **Same CI check fails twice after the same fix pattern** → stop auto-fixing that check, ask the user.
- **Same conflict reappears after a clean rebase** (base branch is re-introducing the conflict) → stop, surface; this usually means the base branch has a parallel PR fighting the same lines.

## Usage

```
/gbase:monitor
```

Typical session:

```
User: /gbase:monitor

Claude: Found PR #142 (feat/user-profile) — state OPEN, 3 checks pending.
         Subscribing… (will auto-fix clear CI/lint failures and address suggested diffs;
         I'll ping you on anything ambiguous.)

[ ~3 min later, Monitor event arrives ]

Claude: CI_FAIL: lint
         eslint reported 2 unused-import errors in src/components/UserProfile.tsx.
         Fixing and pushing.
         → committed as "fix: remove unused imports" (a1b2c3d)

[ ~12 min later ]

Claude: REVIEW_COMMENT from @alice on src/db/schema.ts:42 contains a `suggestion`
         block renaming `userPrefs` → `userPreferences`. Applying.
         → committed as "address review: rename userPrefs to userPreferences" (e4f5g6h)
         → replied "Addressed in e4f5g6h."

[ later ]

Claude: REVIEW_COMMENT from @bob on src/app/api/users/route.ts:88:
         "should this be cached? feels expensive on every request"
         This is a design question, not a directive — surfacing.
         [AskUserQuestion: cache this endpoint?]

[ later ]

Claude: MERGE_CONFLICT — base branch updated.
         Conflicted: pnpm-lock.yaml (lockfile — safe), src/db/schema.ts (semantic — unsafe).
         Aborting rebase, restoring backup stash.
         [AskUserQuestion: schema.ts conflict spans the users table — keep PR side / base side / I'll resolve?]
```
