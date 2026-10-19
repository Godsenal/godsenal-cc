---
name: reproduce
description: "Turns a bug report or an improvement request into an executable check that fails right now — a test, script, HTTP request, CLI run, or verify-skill journey that shows the bug, or a measurement of the requested criterion at its current value — and returns the command, its failing output quoted, and the expected result. Never changes product code. Use before fixing or building, when a bug needs a reproduction or a request needs an acceptance check, or on /gbase:reproduce. gbase:bug-fix starts with it; the fix itself is bug-fix's job."
allowed-tools: Bash Read Write Glob Grep AskUserQuestion Skill
---

# /gbase:reproduce

A fix or an improvement is only provable against a check that failed before it. This writes that check and stops. The check is what `gbase:bug-fix` fixes against and what a later run re-executes to prove the change.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Headless

Before any `AskUserQuestion`, check `printenv AGENT_HEADLESS`; when it prints `1`, follow [headless.md](../../references/headless.md) instead of asking.

## The check

One command, run from the repo root, that exits non-zero now and prints why.

- **Bug** — the wrong behavior on the surface it was reported on. A test in the repo's own runner when a cheap test path exists (it becomes the regression test); otherwise a script, a `curl` against the service, a CLI run, or a journey through the repo's verify skill (`.claude/skills/verify/` or `verify-*`) for UI.
- **Improvement request** — a criterion the requester would accept (a latency, a size, a count, a field a page must render), measured now and asserted against the target, so it fails with the current value in its output. No criterion stated → pick the closest observable one and say which. A pure taste call ("looks nicer") has no check; say so and stop.

## Rules

- **Fails for the stated reason.** Quote the lines that show the bug — the assertion diff, the wrong status and body, the measured value — not just the exit code. An import error, a missing env var, a refused connection, or a typo in the check is a broken check, not a reproduction.
- **Run it twice.** Different results mean flaky: tighten order, timing, seed, or cache until it's stable, or report it as flaky with both outputs. "Passes alone, fails in the full run" is a reproduction once you name what differs.
- **Drive the real path.** No test-only endpoints or internal setters that make the bug appear.
- **Production is read-only.** Against a deployed environment, only requests with no side effects; never create, change, or delete data there.
- **Doesn't reproduce** → report `재현 안 됨` with the conditions tried, and stop. Never weaken the check until it fails.
- **No product code changes.** The only write is a new test file or script, left uncommitted. A fix you can already see goes in the report as a hint.

## Report

```
reproduce: <bug | request> — <한 줄 요약>
command: `<command>`
now (fails):
> <quoted failing lines>
expected: <what the command shows once fixed — the passing assertion, the target value>
files: <added test or script, uncommitted> | none
```

With `AGENT_EVIDENCE_FILE` set, append one `reproduce` [evidence line](../../references/orchestrator.md#evidence-file): `fail` when it reproduced, `pass` when it didn't, `skip` when no executable check was possible.

Suggest `/gbase:bug-fix` for a bug — don't fix it here. When `gbase:bug-fix` called this, return to it.
