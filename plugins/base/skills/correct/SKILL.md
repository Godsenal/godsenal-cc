---
name: correct
description: "Finds the mistakes agents keep repeating in this repo and makes each one impossible: architecture first, then types, then a lint/CI check whose error names the fix, then a test, with REVIEW.md text last. Proves each check fails on a real past mistake. With --session it runs as a retrospective on one coding session instead — where the agent searched too long, lacked information, or made a checkable mistake. Use when the same correction keeps coming back, after a session that was harder than it should have been (\"retro\", \"회고\"), or on /gbase:correct."
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion Agent
---

# /gbase:correct

The operator keeps correcting agents in this repo for the same mistakes. Change the repo so the next agent can't make them. Ported from pstack's `/correct`; `--session` is from Matt Pocock's `retro` (both MIT).

Assume every contributor is an agent that sees only the files it opened, copies the nearest example, and takes the shortest path that compiles. Design the repo so a change that looks right from one file is right for the whole repo.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다. lint 에러 메시지와 `REVIEW.md`/`CLAUDE.md` 문구는 레포 문서의 기존 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking.

## Find the mistake classes

Read recent commits, reverts, PR review comments (`gh api repos/{owner}/{repo}/pulls/<n>/comments`), agent instruction files, and comments that explain workarounds. Past session transcripts (`~/.claude/projects/<cwd-slug>/*.jsonl`) also hold `gbase:review` reports — the fixes made before a PR opened, which never reach GitHub. Group the mistakes into classes. A class counts once it has happened twice.

Check the guardrails too: a check that exists but no hook or CI job runs is the finding — wire it, don't rebuild it.

## --session

A retrospective on one session: the current one by default, or a transcript the user names. A single costly moment counts here, and three more categories apply besides checkable mistakes:

- **Navigation** — a file or fact took many tool calls to find → a one-line pointer from a file the agent already reads.
- **Information access** — the agent needed something it couldn't see → tee the dev-server log to a file, add read-only access to the service.
- **Tool economy** — a call returned far more than it was worth → a narrower command or script.

Every candidate must point at a specific moment in the session. Discard any you can't trace — once the work is done, the pull is to fill the categories with generic advice.

## Fix each class at the highest level that works

1. **Eliminate it with architecture.** Give each piece of state one owner and each task one supported way. Hide internals so the wrong import fails. Replace hand-synced lists with one source of truth. Delete old ways and dead code an agent would copy.
2. **Enforce it with types so the bad state can't be written.** If bad code still compiles, add a lint or CI check whose error names the file, type, or function to use instead. If the pattern is already common, fail only when a change adds more.
3. **Test the behavior.** Fix or delete any test that still passes when the behavior it checks breaks, or that fails when only the internals change.
4. **Write text last, only for judgment calls — in `REVIEW.md`.** `gbase:review` reads it with only a diff in hand; the implementing agent is under the most context pressure and is the wrong place for standards. `CLAUDE.md` loads into every session, so it keeps navigation pointers and the verify block; propose moving other steering out of it.

Show the classes as `class | evidence | level | why not higher` and confirm with `AskUserQuestion` (multiSelect) which to fix now — this changes how every future change here is judged. *headless:* fix every class whose check you can prove on a past instance; the rest become `결정 필요:` lines.

## Fix and prove

Fix the chosen classes, one commit each. Prove each new check fails on a real past mistake (re-apply the old hunk in a scratch `git worktree`), then passes on current code. Run the same command locally and in CI. Exceptions go on the offending line with a reason.

## Keep the rule table

Keep an `## Enforced rules` table at the end of `REVIEW.md` pairing each rule with what enforces it — the reviewer then skips what a check already catches. When the operator corrects you, fix the mistake and add the rule. If the rule was already there and nothing enforces it, that's a repeat, so fix it at the highest level in the same change. Drop a rule once its mistake can't happen.

**Reply:** each class with its evidence, the level you picked, and why a higher level didn't work. Changes stay uncommitted for `/gbase:go`.
