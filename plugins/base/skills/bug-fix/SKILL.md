---
name: bug-fix
description: "Fixes a bug at its root cause, not where it surfaced — reproduces it first, narrows the cause by ruling out hypotheses with runtime evidence, asks whether the triggering state is legitimate before adding any guard, fixes every instance of the pattern, and verifies on the same surface it failed on. Use when asked to fix a bug, when a test or CI fails for a reason that isn't mechanical, or when something 'randomly' breaks or is flaky. When only asked why something broke, it stops at the diagnosis."
allowed-tools: Bash Read Edit Write Glob Grep AskUserQuestion Agent Skill
---

# /gbase:bug-fix

Fix the fault, not the place it became visible. The symptom is where a wrong state showed up; the root cause is the first place the system did something it shouldn't, or failed to handle a state it should. Ported from pstack's `principle-fix-root-causes` and `bug-fix` playbook, with `tdd` and `principle-attack-the-premise` folded in (MIT).

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Every shipped line traces to runtime evidence

A change that "might help" is a hypothesis, not a fix — it doesn't ship. When evidence refutes a hypothesis, revert what it motivated. The smallest change the evidence justifies ships, nothing more.

## Steps

1. **Reproduce it yourself** on the surface where it fails — the test, the CLI, the repo's `verify-*` skill for app behavior. If it won't reproduce, tighten conditions or instrument until it fires; ask the user only with a specific reason the surface can't be reached. "Passes alone, fails in the full run" is a reproduction, not a verdict — find out what differs (load, order, cold cache, shared state).
2. **Narrow the cause** by ruling hypotheses out with runtime evidence (the actual error, the actual state), until the answer is a wrong decision in the code, not a consequence of an earlier one. If the user only asked *why* it broke, stop here and report the diagnosis — don't change code unasked.
3. **Is the triggering state legitimate?** If the system may be in that state, the code that broke on it is the root cause, and handling the state there is the fix. If the state should never exist, a check where it broke hides the bug — find what produced it. Guards, retries, swallowed errors, clamped values, raised timeouts, and discarded state are the usual ways to hide one.
4. **Fix the pattern**, not the instance: find every place with the same fault and fix them together. A workaround that needs a paragraph-long comment means the code is wrong.
5. **Verify on the same surface.** The original reproduction now passes; inconclusive or a different surface is not a pass. Unit tests show branch behavior, not that the bug is gone.
6. **Add the always-on signal** if the deciding fact took a deep dig — the cheap check or log line that would have shown it at first look.

**Two failed fixes on one premise → stop.** Write the premise down as one sentence and test it directly before a third fix; the failures are evidence against it.

## Regression test

When there's a cheap local test path, write the failing test first, run it, and confirm it fails *for the intended reason* before touching the code. Skip it when the test would need broad harness setup, brittle mocks, timing, or production-only state — prefer no test over a bad one, and use the closest rerunnable check (a script, a repro command) instead.

Show the failing-then-passing run in the PR's Evidence. Don't split it into a separate red commit: pre-commit hooks that run tests reject it, per-commit CI and `git bisect` trip on it, and a squash merge erases the order anyway.

## Reply

Include why the triggering state was or wasn't legitimate, and paste the failing-then-passing output verbatim. Suggest `/gbase:go` to ship — don't run it; pushing is the user's call.
