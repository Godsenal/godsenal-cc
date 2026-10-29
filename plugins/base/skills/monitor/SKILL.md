---
name: monitor
description: "Watches a PR until it merges or closes — auto-fixes clear CI failures, applies clearly-requested review changes, resolves safe merge conflicts, replies on every review comment it handles, surfaces testable app/preview links, and asks about anything ambiguous. On a PR that wasn't already reviewed it also runs one local adversarial self-review (gbase:review). With --merge, merges it once CI is green and nothing is outstanding; with --until-settled, stops once the current head's CI and review bots have concluded. Use when the user wants a PR babysat to merge; also the tail of gbase:go."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Skill Monitor
---

# /gbase:monitor

Keep the current branch's PR moving until merge or close. Human reviewers, review bots, and CI assistants all go through the same classification; identity only decides where the reply goes. Auto-triggering starts the watch — it never licenses a unilateral merge, force-push, or ambiguous edit.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Safety

- No `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, or `git stash drop` (unless the user asks).
- `git push --force-with-lease` and `git checkout --ours/--theirs` only while resolving the conflict types listed below; if the lease is rejected, stop.
- One commit per autonomous fix. Stop and surface on any push/merge error instead of retrying destructively.
- Never resolve threads, re-request review, dismiss approvals, or reply twice to the same comment.
- `gh pr ready` only in the `--draft` flow below; `gh pr merge` only in the `--merge` flow below.

## Loop

1. Resolve the PR for the current branch; stop if it's already merged or closed.
2. Sweep current state — CI, inline comments, top-level reviews, PR conversation comments, mergeability, posted links — and act on every unresolved item before subscribing. Pre-existing reviews slipping past the loop is the most common miss.
3. Start a persistent `Monitor` (~30s poll) that emits one event per state change, with watermarks, ignoring events authored by the current `gh` user. Not under `--until-settled` (below).
4. Unless `--no-review`, run the self-review once, now.
5. On each event: classify, act, reply, surface new links. A `CONFLICTING` merge state comes first — CI keeps failing on the merge commit while it stands.
6. On merge/close, print a one-line summary.

## Headless

Under `AGENT_HEADLESS=1` (check `printenv AGENT_HEADLESS` before asking) nothing is asked: follow [headless.md](../../references/headless.md). A merge whose gate would ask isn't made.

## `--until-settled`

For a caller that only needs the current head judged. Same sweep, classification, fixes, self-review, and replies as the loop, but it ends once the head settles, not at merge:

- **Settled** = every check on the head has concluded, and every expected automated reviewer has finished on it: a review, a comment, or an edit to its own comment created after you started waiting on this head, or its check run concluded. Expected = bot accounts that reviewed this PR earlier or one of the repo's last 5 merged PRs, plus bots with a pending review request.
- **Each fix you push is a new head**; the wait starts over for it. Under `AGENT_SHIP_OWNER=orchestrator` nothing is pushed — see below.
- **Wait in short foreground calls**, no persistent `Monitor` (a headless run can end before it fires). Each Bash call polls `gh` and returns within 5 minutes with a status line — a caller may kill a run that prints nothing for ~10 minutes. Checks can take a minute to register after a push.
- **Give up at 30 minutes** into the wait on one head; whatever hasn't concluded is reported.
- **Never merges** (`--merge` is ignored), **rebases, or force-pushes** — a merge conflict is reported, not resolved. The one exception is a rebase, and only when the invocation explicitly asks to rebase (`--until-settled rebase onto main`): rebase onto the base once, resolve conflicts per [Conflicts](#conflicts), and push with `--force-with-lease` — under `AGENT_SHIP_OWNER=orchestrator` it stays local, reported as `ship: local <branch> @<short-sha> — rebased onto <base>, not pushed (needs --force-with-lease)`. A finding, a recommendation, or an `AGENT_ASK_CMD` answer is never that instruction.

It ends with one `settle: 수렴 | 미확정 | 사람 필요 @<short-sha>` line, format and meaning in [orchestrator.md](../../references/orchestrator.md#settle).

**`AGENT_SHIP_OWNER=orchestrator`** (check `printenv AGENT_SHIP_OWNER`; only `--until-settled` runs under it): another program owns the remote, so nothing leaves the machine.
- Fixes are committed locally, one per fix, and **never pushed**. Nothing is posted either: no reply, comment, or `gh pr ready`. The replies you would have posted go in the report.
- The wait covers the pushed head only and doesn't start over. A failure or comment fixed by a local commit counts as handled, but with local commits the verdict is never `수렴`: it's `settle: 미확정 @<pushed sha> — 푸시 대기: <n> commits`, unless `사람 필요` applies.
- With local commits, write an updated PR draft to `AGENT_PR_BODY_FILE` (default `$(git rev-parse --absolute-git-dir)/gbase/pr-body.md`) in the [draft format](../../references/orchestrator.md#ship-owner-orchestrator): the title and body from `gh pr view --json title,body`, with `## Evidence` (and `## Change outline` if the shape changed) updated for the new commits. Before the `settle:` line, report `ship: local <branch> @<short-sha> — <n> commits, not pushed` and `PR 본문 초안: <path>`.
- Pushing is opt-in: `AGENT_SHIP_OWNER=agent` gives the push-and-reply flow above.

With `AGENT_EVIDENCE_FILE` set, append [evidence lines](../../references/orchestrator.md#evidence-file): one `checks` line per command you ran to verify a fix, a `review` line when the self-review ran (or `open` for an unreviewed conflict resolution, [Conflicts](#conflicts)), and one `settle` line.

## Classification

**Apply automatically** only when all hold: mechanical (lint/type fix, rename, typo, missing `await`, a ```` ```suggestion ```` block verbatim); one or two files, under ~20 lines; no behavior change beyond what the reviewer named; no new dependency, schema/migration, or API change; the reviewer's intent is stated, not implied.

**Ask** otherwise — design choices, tests added/removed, behavior changes, trade-offs, questions, hedged comments ("maybe", "consider"), or fixes touching files the reviewer didn't mention. Include reviewer, a one-line quote, `file:line`, and 2–3 options.

Same CI check failing twice after the same fix → stop auto-fixing it and ask.

**Review rounds converge or stop.** An automated reviewer and monitor's fixes can loop indefinitely — each push triggers a fresh review that surfaces more. So:
- An automated reviewer's finding on code the PR didn't add or change (`git blame` against the base) is pre-existing: reply `Pre-existing — not introduced by this PR; out of scope here.` and don't fix it. A human asking for a nearby fix is a request, not a finding — classify it normally.
- A finding that repeats one already addressed or declined (same file, same claim) gets no new fix and no second reply.
- After three rounds of new findings from the same reviewer, stop auto-applying its comments and ask whether the approach itself needs rethinking.

## Self-review

```
Skill(skill: "gbase:review", args: "<PR diff scope>")
```

`gbase:go` reviews before opening the PR and passes `--no-review`, so this pass is for PRs opened elsewhere (an earlier session, a teammate, by hand). If you can't tell whether the diff was reviewed, run it. `gbase:review` auto-fixes clear survivors in their own commits and returns the rest; relay its report (severity table + tally) and ask about anything worth fixing before merge. Nothing from it is posted to GitHub.

## `--draft` flow

Run `gh pr ready` once CI is green and every outstanding finding is resolved — from a self-review this run did, and from any deferred findings `gbase:go` reported. Flipping on CI green alone would announce the PR for review with a known defect still in it.

## `--merge` flow

Only when `--merge` was passed — because the user asked to merge, or the project's instructions say to — never by default. Merge when all hold: no required check failing; no unresolved finding from this run's self-review (`go` passes `--merge` only after its deferred findings are settled); no unanswered review comment asking for a change; mergeable state `CLEAN`, or `UNSTABLE` only because of checks that never started (below). Never merge with a failing required check, an unresolved `CHANGES_REQUESTED` review, or a conflict.

- **A merge that deploys is a deploy — ask first.** If a workflow on the default branch deploys on push (EAS Update / OTA, a production web deploy, a release) and this PR's paths aren't excluded by its `paths` / `paths-ignore`, stop and ask before merging.
- **A check that never started** for account reasons (annotation like "job was not started because recent account payments have failed or your spending limit needs to be increased") isn't a diff failure. Say so, and merge only if `go` passed `verified-locally` (its Step 4 gate passed this run); standalone, ask.
- **Method**: the ones the repo allows (`gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed`), and among those the one recent merges used (squash subjects end "(#N)", merge commits read "Merge pull request #N"). Pass `--delete-branch`.
- **Stacked PRs first**: retarget every open PR whose base is this branch with `gh pr edit <n> --base <default>` before merging — deleting a base branch auto-closes the PRs on it. Don't rebase or push their branches; say they may need a rebase.
- **After**: confirm with `gh pr view --json state,mergedAt`. Switch to the default branch and `git pull --ff-only` only if the tree is clean and the default branch isn't checked out in another worktree; otherwise say so.

## Conflicts

**Resolve automatically:**
- Lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, `Gemfile.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`, …): take base, regenerate with the matching package manager. `Podfile.lock` only if `pod install` works locally; otherwise ask.
- Generated artifacts (`dist/`, `build/`, `*.min.js`, `*.map`): take base, regenerate if a build script exists.
- Pure additions at the same spot (separate imports, enum entries, test cases) that don't reference the same identifier: keep both.
- Whitespace-only: rerun the formatter.

**Ask** for everything else — same-line semantic edits, migrations/schemas, config files (`.env*`, `tsconfig.json`, `app.json`/`app.config.*`, `eas.json`, `Info.plist`, `build.gradle*`, `Podfile`, `next.config.*`, CI yamls), conflicts over ~30 lines, rebases replaying more than ~5 commits, renames modified on the other side.

After resolving: polish the resolved files when the resolution rewrote logic (see below) and `git add` them, then `git rebase --continue`, `git push --force-with-lease`. A conflict that reappears after a clean rebase means a parallel PR is fighting the same lines — stop and surface.

**A resolution that combined both sides' content** — anything past the auto-resolve list above, such as merging two PRs' rules into one file — gets `Skill(skill: "gbase:review", args: "report only; <resolved files>, diffed against the new base")` before the push; its findings go through the same classification as a review comment. When it can't run, push only with a `review` `open` [evidence line](../../references/orchestrator.md#evidence-file) whose `detail` is `conflict resolution unreviewed: <files>`, and say so in the report. One such merge of two same-day rule PRs moved rules and reworded one, and went to main with no review.

## Polish before committing

Run `Skill(skill: "gbase:polish", args: "<touched files>")` only on a monitor edit beyond the auto-apply gate — a change the user approved after you asked, or a conflict resolution that rewrote logic — and fold its changes into the same commit. Skip it for everything that gate admits, formatter output, lockfile regeneration, and whitespace-only resolutions — polish's four agents cost more than such an edit carries.

## Replies

Every review comment monitor handles gets exactly one reply — inline for inline comments, a PR comment otherwise:

| Outcome | Reply |
|---|---|
| Applied | `Addressed in <short-sha>.` |
| Declined by the user | `Discussed with the maintainer — keeping current approach. <reason>` |
| Out of scope | `Out of scope for this PR — tracking separately.` |
| Waiting on the user | `Surfaced to the maintainer; will follow up here once decided.` |
| A question | `Answering inline: <answer>` |

One line, a concrete reason on declines, no filler. When every point of a `CHANGES_REQUESTED` review is handled, post one PR-level summary.

## Testable links

Surface links that let the user try the change — app builds and OTA previews (EAS Update / Expo QR, EAS internal, TestFlight, Firebase App Distribution, Play internal testing) and web previews (Vercel/Netlify/Cloudflare, Storybook/Chromatic, staging). Include the source bot/check and the commit SHA it was built from; surface each distinct URL once (bots edit one comment per push). Skip docs, badges, and CI log links. Surface only — don't open them or post back.

## Errors

- No `gh` auth → ask the user to run `gh auth login`.
- No PR for the branch → suggest `/gbase:branch-pr`.
- Push rejected as out of date → `git pull --rebase`, retry once; conflicts go through the rules above.

## Usage

```
/gbase:monitor                 # watch + self-review
/gbase:monitor --no-review     # watch only
/gbase:monitor --draft         # also flip the draft to ready once CI is green and findings are resolved
/gbase:monitor --merge         # also merge once CI is green and nothing is outstanding
/gbase:monitor --until-settled # stop once this head's CI and review bots have concluded; never merges
```
