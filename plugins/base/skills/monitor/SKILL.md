---
name: monitor
description: "Watch a PR until merge/close — auto-fix clear CI failures, address clearly-needed review comments, resolve safe merge conflicts (lockfiles, pure additions), and run /gbase:polish on every non-trivial auto-edit before committing. Ask on ambiguous ones. Invoke manually with /gbase:monitor or chained from /gbase:go; do not trigger automatically."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Skill Monitor
---

# /gbase:monitor

Subscribe to the current branch's PR and keep it moving until it merges or closes. Apply clear review feedback, fix obvious CI failures, resolve safe merge conflicts. Surface anything subjective via `AskUserQuestion`.

Reviewer-agnostic: human reviewers, code review bots, and CI assistants go through the same classification. Identity matters for the *reply target*, not for whether to engage.

Invoke explicitly via `/gbase:monitor` or as the tail of `/gbase:go`.

## Safety rules

- Prohibited: `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, `git stash drop` (unless the user explicitly asks).
- **Conflict rebases only**: `git push --force-with-lease` is allowed (refuses if the remote moved); `git checkout --ours/--theirs <file>` is allowed for the cases listed in [Conflict classification](#conflict-classification). Never as a shortcut on a semantic conflict.
- Snapshot before any rebase. On uncertainty: `git rebase --abort`.
- Each autonomous fix is its own commit with a clear message.
- Stop and surface on any push/merge error; never retry destructively.
- Never resolve a review thread, re-request review, or dismiss approvals on the user's behalf.
- Never reply twice to the same comment.

## Loop

1. Resolve the PR for the current branch. Stop if it's already `MERGED` / `CLOSED`.
2. Sweep current state — CI, every review surface GitHub exposes (inline comments, top-level reviews, PR conversation comments), and mergeability. **Act on every unresolved item before subscribing** — don't just watermark them. Pre-existing reviews slipping past the loop is the most common failure mode.
3. Start a persistent `Monitor` (~30s poll). Emit one event per state change; watermark to avoid re-emission. Skip events authored by the current gh user so your own replies don't loop back.
4. On each event: classify, act, reply (when applicable).
5. Exit when state flips to `MERGED` / `CLOSED`. Print a one-line summary.

If `mergeable` is `CONFLICTING` at any point, handle the conflict first — CI runs on the merge commit and keeps failing while it stands.

## Classification: clear vs ambiguous

**Apply automatically** when ALL hold:

- Mechanical: rename, formatting, lint/typecheck fix, unused-import/variable removal, missing-await, obvious typo, applying a fenced ` ```suggestion ` block verbatim.
- Local (one or two files, under ~20 lines of diff).
- No behavior change beyond what the reviewer explicitly named.
- No new dependency, no schema/migration, no API contract change.
- Reviewer's intent is stated directly, not implied.

**Ask the user** when ANY hold:

- Architecture, abstraction, or design choice.
- Test added or removed.
- Behavior change ("we should also handle X").
- Performance trade-off, new dependency, schema/migration.
- Comment is a question, not a request.
- Reviewer hedges ("maybe", "consider", "could we...").
- Fix would touch files the reviewer didn't reference.

When in doubt, ask. Include reviewer + a one-line quote + `file:line` + 2–3 concrete options.

## Conflict classification

**Resolve automatically**:

- **Lockfiles** (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, `Gemfile.lock`, `poetry.lock`, `Cargo.lock`, `composer.lock`, `go.sum`): take the base side, regenerate via the matching package manager, `git add`.
- **Generated/build artefacts** (`dist/`, `build/`, `*.min.js`, `*.map`): take base side, regenerate if a `build` script exists.
- **Pure-addition conflicts** where both sides added independent content at the same location (separate enum entries, separate imports, separate test cases): keep both. The two blocks must not reference the same identifier.
- **Whitespace-only conflicts**: rerun the project's formatter, `git add`.

**Ask** for everything else: same-line semantic edits, migrations/schemas, config files (`.env*`, `tsconfig.json`, `next.config.*`, CI yamls), conflicts spanning more than ~30 lines, rebase replays of more than ~5 commits, renames where the other side modified the old path.

After resolving, `git rebase --continue`, run [Post-fix polish](#post-fix-polish) on resolved non-lockfile files, then `git push --force-with-lease`. If `--force-with-lease` is rejected, stop and surface.

## Post-fix polish

Whenever monitor produces a code edit, run the `gbase:polish` skill on touched files **before** staging — fold any resulting edits into the same commit. Polish does deslop + structural passes (both behavior-preserving), so monitor's auto-fix doesn't ship with leftover AI cruft or premature abstractions.

```
Skill(skill: "gbase:polish", args: "<touched files>")
```

**Skip** when the edit is provably mechanical and re-running would be a no-op: lint/format auto-fix output, verbatim ` ```suggestion ` block application, lockfile regen, whitespace-only.

## Always reply

Every review comment monitor touches gets exactly one reply, regardless of outcome. Inline comments get an inline reply; PR-level items get a PR conversation comment.

| Outcome | Reply template |
|---|---|
| Applied (auto or after `AskUserQuestion` confirmed) | `Addressed in <short-sha>.` |
| Declined (user picked "skip") | `Discussed with the maintainer — keeping current approach. <one-line reason>` |
| Declined (clearly out of scope) | `Out of scope for this PR — tracking separately.` |
| Deferred | `Surfaced to the maintainer; will follow up here once decided.` |
| Question, not a request | `Answering inline: <one-line answer>` (or surface to the maintainer if unknown) |

Tone: one line, concrete reason on declines, no apology or "thanks for the feedback" filler. Never resolve the thread; the reviewer does that.

When all points of a `CHANGES_REQUESTED` review are resolved, post a single PR-level summary so the reviewer doesn't crawl every thread.

## Error handling

- `gh` auth missing → stop, ask the user to run `gh auth login`.
- No PR for branch → stop, suggest `/gbase:branch-pr`.
- Push rejected (branch out of date) → `git pull --rebase`, retry once. Conflicts → hand off to conflict handling.
- `--force-with-lease` rejected → stop, surface; do not retry.
- Same CI check fails twice after the same fix pattern → stop auto-fixing that check, ask.
- Same conflict reappears after a clean rebase → stop, surface (base branch likely has a parallel PR fighting the same lines).

## Usage

```
/gbase:monitor
```
