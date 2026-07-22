---
name: monitor
description: "Watch a PR until merge/close — auto-fix clear CI failures, address clearly-needed review comments, resolve safe merge conflicts (lockfiles, pure additions), surface testable preview/deploy links from CI/bot comments, and run /gbase:polish on every non-trivial auto-edit before committing. Also runs one post-PR self-review (gbase:review — our own adversarial review skill) in parallel with the watch — findings are verified against independent skeptics, classified like reviewer comments, and reported to the user, never posted to GitHub (--no-review skips it). Ask on ambiguous ones. Invoke manually with /gbase:monitor, chained from /gbase:go, or auto-triggered when the user wants a PR babysat until it merges; the persistent Monitor and AskUserQuestion gates keep it from acting unilaterally on anything ambiguous."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Skill Monitor
---

# /gbase:monitor

Subscribe to the current branch's PR and keep it moving until it merges or closes. Apply clear review feedback, fix obvious CI failures, resolve safe merge conflicts. Surface anything subjective via `AskUserQuestion`. Surface testable preview/deploy links that CI or bots post so the user can try the change. Run one adversarial self-review of the PR (`gbase:review`) right after the watch starts — review costs the ship path nothing because it runs inside the CI wait the PR already pays.

Reviewer-agnostic: human reviewers, code review bots, and CI assistants go through the same classification. Identity matters for the *reply target*, not for whether to engage.

Model-invocable: invoke explicitly via `/gbase:monitor`, as the tail of `/gbase:go`, or let the model trigger it when the user asks to keep a PR moving until merge. The persistent `Monitor` and the `AskUserQuestion` gates on ambiguous items mean auto-triggering only starts the watch loop — it never green-lights a unilateral edit, merge, or force-push.

## Safety rules

- Prohibited: `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, `git stash drop` (unless the user explicitly asks).
- **Conflict rebases only**: `git push --force-with-lease` is allowed (refuses if the remote moved); `git checkout --ours/--theirs <file>` is allowed for the cases listed in [Conflict classification](#conflict-classification). Never as a shortcut on a semantic conflict.
- Snapshot before any rebase. On uncertainty: `git rebase --abort`.
- Each autonomous fix is its own commit with a clear message.
- Stop and surface on any push/merge error; never retry destructively.
- Never resolve a review thread, re-request review, or dismiss approvals on the user's behalf.
- `gh pr ready` (draft → ready) only in the [`--draft` flow](#--draft-flow) the user opted into; never flip a draft the user created themselves.
- Never reply twice to the same comment.

## Loop

1. Resolve the PR for the current branch. Stop if it's already `MERGED` / `CLOSED`.
2. Sweep current state — CI, every review surface GitHub exposes (inline comments, top-level reviews, PR conversation comments), mergeability, and any testable links already posted (see [Surface testable links](#surface-testable-links)). **Act on every unresolved item before subscribing** — don't just watermark them. Pre-existing reviews slipping past the loop is the most common failure mode.
3. Start a persistent `Monitor` (~30s poll). Emit one event per state change; watermark to avoid re-emission. Skip events authored by the current gh user so your own replies don't loop back.
4. Run the [Self-review](#self-review) pass — once, now, while the watch runs in the background.
5. On each event: classify, act, reply (when applicable), and surface any new testable link.
6. Exit when state flips to `MERGED` / `CLOSED`. Print a one-line summary (including the self-review tally).

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

## Self-review

One pass per watch, right after the `Monitor` starts (loop step 4) — never before the PR exists, so it
adds nothing to the time-to-PR. Skip on `--no-review`.

```
Skill(skill: "gbase:review", args: "<PR diff scope>")
```

`gbase:review` is our own **adversarial** review skill (the built-in `code-review` is no longer
model-invocable). It finds defects along the built-in's dimensions, then makes each finding survive an
independent skeptic before returning it — and it already does the [classification](#classification-clear-vs-ambiguous)
below internally, auto-fixing clear+local survivors in their own commits and returning the rest as a
report. Monitor just relays that report; the split is:

- **Clear** (mechanical, local, concrete failure scenario — missing `await`, inverted condition,
  wrong-variable copy-paste) → auto-fixed by `gbase:review`: own commit, [post-fix polish](#post-fix-polish), push.
- **Everything else** → in the report; anything worth fixing before merge gets an `AskUserQuestion`.

Differences from external review comments:

- **Nothing is posted to GitHub** — no comments, no replies, no reviews. Findings go to the user; fixes
  show up as commits.
- **One organized report** when the pass finishes: a severity-ordered table
  `# | file:line | finding | action (auto-fixed <sha> / needs decision / noted)`, then a one-line tally:
  `review: F found, R refuted, S survived — A auto-fixed, K for you`.
- **PR merged before the pass finished** (fast CI, auto-merge): don't push to the merged branch — report
  the remaining findings as follow-up-PR candidates.

### `--draft` flow

When invoked with `--draft` (usually passed through from `gbase:go`, with `branch-pr` having opened the
PR as a draft): once CI is green **and** every self-review finding is resolved (auto-fixed or decided by
the user), run `gh pr ready` and tell the user. This is the only case where monitor may flip draft
state, and only because the flag was the user's opt-in.

## Conflict classification

**Resolve automatically**:

- **Lockfiles** (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, `Gemfile.lock`, `poetry.lock`, `Cargo.lock`, `composer.lock`, `go.sum`): take the base side, regenerate via the matching package manager, `git add`.
- **Generated/build artefacts** (`dist/`, `build/`, `*.min.js`, `*.map`): take base side, regenerate if a `build` script exists.
- **Pure-addition conflicts** where both sides added independent content at the same location (separate enum entries, separate imports, separate test cases): keep both. The two blocks must not reference the same identifier.
- **Whitespace-only conflicts**: rerun the project's formatter, `git add`.

**Ask** for everything else: same-line semantic edits, migrations/schemas, config files (`.env*`, `tsconfig.json`, `next.config.*`, CI yamls), conflicts spanning more than ~30 lines, rebase replays of more than ~5 commits, renames where the other side modified the old path.

After resolving, `git rebase --continue`, run [Post-fix polish](#post-fix-polish) on resolved non-lockfile files, then `git push --force-with-lease`. If `--force-with-lease` is rejected, stop and surface.

## Surface testable links

CI checks and deploy/preview bots routinely post links you can open to *try the change* — Vercel/Netlify/Cloudflare preview deployments, Storybook/Chromatic builds, staging or review-app URLs, "View deployment" targets on a check run. When one shows up, surface it to the user inline so they can click through and test. Bots usually label these clearly — use judgment; you don't need an exhaustive allowlist.

- **Surface**: links whose purpose is testing the change (preview / deploy / staging / review-app / storybook / demo).
- **Skip**: links that aren't for testing — docs, issue/PR/commit references, coverage badges, dashboards, CI log/run URLs.
- **Include context**: the URL, its source (which bot/check), and the commit SHA it was built from, so the user knows which revision they're testing.
- **Dedup**: surface each distinct URL once. Preview bots edit the same comment per push — when the URL changes (new deployment), surface the new one once; never re-emit an unchanged URL.
- **Surface only**: don't open it, smoke-test it, or post anything back to the PR. This is purely informational for the user. No new side effects, no `allowed-tools` beyond what monitor already has.

Catch already-posted links during the initial sweep; catch new ones on each event.

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
/gbase:monitor                 # watch + self-review
/gbase:monitor --no-review     # watch only
/gbase:monitor --draft         # also flip the draft PR to ready once CI is green + self-review resolved
```
