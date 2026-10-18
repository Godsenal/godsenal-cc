---
name: correct
description: "Finds the mistakes agents keep repeating in this repo — from the gbase ledger (review findings, CI failures, review comments that gbase:review and gbase:monitor record), reverts, and PR review history — and makes each recurring class impossible: architecture first, then types, then a lint/CI check whose error names the fix, then a test, with REVIEW.md text last. Proves each new check fails on a real past instance. With --session it runs as a retrospective on one coding session instead — where the agent searched too long, lacked information, or made a checkable mistake — and routes each to a pointer, access, or check. Use when the same correction keeps coming back, after a session that was harder than it should have been ("retro", "회고"), periodically after a batch of PRs, or on /gbase:correct."
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion Agent
---

# /gbase:correct

The repo should make the wrong change hard to write, not rely on the next agent reading a rule. Assume every contributor is an agent that sees only the files it opened, copies the nearest example, and takes the shortest path that compiles. Adapted from pstack's `/correct` and Matt Pocock's `retro` (MIT).

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 이 규칙이 아니라 레포의 기존 관례(`git log`, 최근 PR)를 따른다. lint 에러 메시지와 `CLAUDE.md`/`REVIEW.md` 문구는 레포 문서의 기존 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## 1. Gather evidence

- **Ledger** — `~/.claude/gbase/ledger/<owner>_<repo>.tsv` (columns: date, pr, source, category, file, outcome, summary), written by `gbase:review` and `gbase:monitor`.
- **Reverts and fix-ups** — `git log --grep='^Revert' --grep='^fix' -i` over recent history, with the commit each one fixed.
- **Review history** — inline comments on the last ~20 merged PRs (`gh api repos/{owner}/{repo}/pulls/<n>/comments`); skip ones the ledger already covers.
- **Existing rules and guardrails** — `CLAUDE.md`, `AGENTS.md`, `REVIEW.md`, lint config, pre-commit hooks, CI workflows, and comments explaining workarounds. A check that exists but isn't wired into a hook or CI is the finding — wire it, don't rebuild it. A repo where no hook or CI job runs lint/typecheck/tests is a finding on its own.

With `--session`, the source is one session instead: the current conversation by default, or a transcript the user names (`~/.claude/projects/<cwd-slug>/<id>.jsonl`). There a single costly moment counts, and the categories widen:

- **Navigation** — a file or fact took many tool calls to find → a one-line pointer from a file the agent already reads.
- **Information access** — the agent needed something it couldn't see (dev-server logs, a service's state) → tee the log to a file, add read-only access.
- **Tool economy** — a call that returned far more than it was worth → a narrower command or script.
- **Checkable mistake** — goes through the ladder in step 2.

**Every candidate must cite its evidence** — a ledger line, a commit, a review comment, or a specific session moment. Discard any you can't trace; once the work is done, the pull is to fill categories with generic advice.

Group into classes by root cause, not wording. **A class counts once it has happened twice**; one-offs are noise. Outcome `declined` entries are evidence the reviewer was wrong — they argue for a `REVIEW.md` skip or severity rule, not a code check.

## 2. Pick the highest level that works, per class

1. **Architecture** — one owner per piece of state, one supported way per task; hide internals so the wrong import fails; replace hand-synced lists with one source of truth; delete the old way an agent would copy.
2. **Types** — make the bad state unrepresentable.
3. **Lint / CI check** — when bad code still compiles. The error message names the file, type, or function to use instead. If the pattern is already common, fail only on additions.
4. **Test** — on behavior; also fix or delete a test that still passes when its behavior breaks.
5. **Text last, for the reviewer** — judgment calls go in `REVIEW.md`, which `gbase:review` reads with only a diff in hand; the implementing agent is under the most context pressure and is the wrong place to enforce standards. Nothing fails when an agent skips text.

`CLAUDE.md` loads into every session, so it holds navigation pointers and the verify block, little else. When it's large, propose moving its steering into `REVIEW.md` or a check, and deleting lines that change no behavior.

Present the classes as a table — `class | occurrences (evidence) | level | why not higher` — and confirm with `AskUserQuestion` (multiSelect) which to fix now. This changes how every future change in the repo is judged; don't apply unasked.

## 3. Fix and prove

One commit-sized change per class. **Prove each new check fails on a real past instance** — re-apply the offending hunk from the ledger/revert in a scratch copy or `git worktree`, run the check, see it fail, then see it pass on current code. A check that never failed on a real mistake is untested. Run the same command locally and in CI (add it to the workflow if it isn't picked up). Exceptions go on the offending line with a reason.

## 4. Keep the rule table

Maintain an `## Enforced rules` table at the end of `REVIEW.md`: `rule | enforced by (check / type / test / text)` — the reviewer then skips what a check already catches. If a correction repeats a rule that's already there with only text behind it, that's a repeat — move it up a level in the same change. Drop a rule once its mistake can't happen, and propose removing a check whose ledger hits are mostly `declined` — it fires on good code.

## Report

Per class: evidence, level chosen and why a higher one didn't work, the proof (command + fail → pass). Then what was left as text and why. Changes stay uncommitted for `/gbase:go`.
