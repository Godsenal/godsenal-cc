---
name: monitor
description: "Watches a PR until it merges or closes — auto-fixes clear CI failures, applies clearly-requested review changes, resolves safe merge conflicts, replies on every review comment it handles, surfaces testable app/preview links, and asks about anything ambiguous. On a PR that wasn't already reviewed it also runs one local adversarial self-review (gbase:review). Use when the user wants a PR babysat to merge; also the tail of gbase:go."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Skill Monitor
---

# /gbase:monitor

Keep the current branch's PR moving until merge or close. Human reviewers, review bots, and CI assistants all go through the same classification; identity only decides where the reply goes. Auto-triggering starts the watch — it never licenses a unilateral merge, force-push, or ambiguous edit.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 이 규칙이 아니라 레포의 기존 관례(`git log`, 최근 PR)를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Safety

- No `git reset --hard`, `git checkout .`, `git clean -f`, plain `git push --force`, or `git stash drop` (unless the user asks).
- `git push --force-with-lease` and `git checkout --ours/--theirs` only while resolving the conflict types listed below; if the lease is rejected, stop.
- One commit per autonomous fix. Stop and surface on any push/merge error instead of retrying destructively.
- Never resolve threads, re-request review, dismiss approvals, or reply twice to the same comment.
- `gh pr ready` only in the `--draft` flow below.

## Loop

1. Resolve the PR for the current branch; stop if it's already merged or closed.
2. Sweep current state — CI, inline comments, top-level reviews, PR conversation comments, mergeability, posted links — and act on every unresolved item before subscribing. Pre-existing reviews slipping past the loop is the most common miss.
3. Start a persistent `Monitor` (~30s poll) that emits one event per state change, with watermarks, ignoring events authored by the current `gh` user.
4. Unless `--no-review`, run the self-review once, now.
5. On each event: classify, act, reply, log it to the ledger (below), surface new links. A `CONFLICTING` merge state comes first — CI keeps failing on the merge commit while it stands.
6. On merge/close, print a one-line summary.

## Classification

**Apply automatically** only when all hold: mechanical (lint/type fix, rename, typo, missing `await`, a ```` ```suggestion ```` block verbatim); one or two files, under ~20 lines; no behavior change beyond what the reviewer named; no new dependency, schema/migration, or API change; the reviewer's intent is stated, not implied.

**Ask** otherwise — design choices, tests added/removed, behavior changes, trade-offs, questions, hedged comments ("maybe", "consider"), or fixes touching files the reviewer didn't mention. Include reviewer, a one-line quote, `file:line`, and 2–3 options.

Same CI check failing twice after the same fix → stop auto-fixing it and ask.

**Review rounds converge or stop.** An automated reviewer and monitor's fixes can loop indefinitely — each push triggers a fresh review that surfaces more. So:
- An automated reviewer's finding on code the PR didn't add or change (`git blame` against the base) is pre-existing: reply `Pre-existing — not introduced by this PR; logged for follow-up.` and don't fix it. A human asking for a nearby fix is a request, not a finding — classify it normally.
- A finding that repeats one already addressed or declined (same file, same claim) gets no new fix and no second reply.
- After three rounds of new findings from the same reviewer, stop auto-applying its comments and ask whether the approach itself needs rethinking.

## Ledger

Append one line per CI failure fixed and per review comment handled to the gbase ledger (`~/.claude/gbase/ledger/<owner>_<repo>.tsv`, same slug command as `gbase:review` — `origin` URL, else the repo's local path; `mkdir -p` its directory first) — one tab-separated line: `date, pr, source, category, file, outcome, summary`, with source `ci` or `review-comment`, a short kebab-case `category` reused from the file when one fits, and outcome `fixed` / `declined` / `deferred` / `pre-existing`. `gbase:correct` mines it.

## Self-review

```
Skill(skill: "gbase:review", args: "<PR diff scope>")
```

`gbase:go` reviews before opening the PR and passes `--no-review`, so this pass is for PRs opened elsewhere (an earlier session, a teammate, by hand). If you can't tell whether the diff was reviewed, run it. `gbase:review` auto-fixes clear survivors in their own commits and returns the rest; relay its report (severity table + tally) and ask about anything worth fixing before merge. Nothing from it is posted to GitHub.

## `--draft` flow

Run `gh pr ready` once CI is green and every outstanding finding is resolved — from a self-review this run did, and from any deferred findings `gbase:go` reported. Flipping on CI green alone would announce the PR for review with a known defect still in it.

## Conflicts

**Resolve automatically:**
- Lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, `Gemfile.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`, …): take base, regenerate with the matching package manager. `Podfile.lock` only if `pod install` works locally; otherwise ask.
- Generated artifacts (`dist/`, `build/`, `*.min.js`, `*.map`): take base, regenerate if a build script exists.
- Pure additions at the same spot (separate imports, enum entries, test cases) that don't reference the same identifier: keep both.
- Whitespace-only: rerun the formatter.

**Ask** for everything else — same-line semantic edits, migrations/schemas, config files (`.env*`, `tsconfig.json`, `app.json`/`app.config.*`, `eas.json`, `Info.plist`, `build.gradle*`, `Podfile`, `next.config.*`, CI yamls), conflicts over ~30 lines, rebases replaying more than ~5 commits, renames modified on the other side.

After resolving: `git rebase --continue`, polish the resolved non-lockfile files, `git push --force-with-lease`. A conflict that reappears after a clean rebase means a parallel PR is fighting the same lines — stop and surface.

## Polish before committing

Run `Skill(skill: "gbase:polish", args: "<touched files>")` on every non-trivial monitor edit and fold its changes into the same commit. Skip for formatter output, verbatim suggestion blocks, lockfile regeneration, and whitespace-only resolutions.

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
```
