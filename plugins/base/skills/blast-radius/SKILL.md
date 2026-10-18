---
name: blast-radius
description: "Finds what a change could break somewhere else before it ships — beyond the diff, where grep stops — and proves the one fact it's safe because of by running real code instead of writing it up. Use for 'blast radius of X', 'what could this break', '이거 뭐 깨질 수 있어', or a small diff you don't trust yet."
allowed-tools: Bash Read Write Glob Grep
---

# /gbase:blast-radius

Find what a change breaks somewhere else, before it ships. Ported from pstack's `blast-radius` (MIT).

Listing the callers is not the job — that's a grep. The job is the breakage grep won't show you. Deploy-ordering hazards (migrations, contract skew, env, old app versions) belong to `gbase:compat-check`; hand them there instead of covering them twice.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 이 규칙이 아니라 레포의 기존 관례(`git log`, 최근 PR)를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Don't trust your own writeup

A blast-radius writeup that sounds right is worthless — it reads as convincing whether or not it's true. Find the one or two facts the whole thing depends on and prove them by running code.

For each fact the change's safety depends on, get it as far down this list as is cheap, and say where it stopped:

1. You said so. Worthless on its own.
2. You pointed at the line — a real `file:line`, or the library's own source.
3. You showed the bad case can't happen — walked the failure step by step and it doesn't reach.
4. You ran it — a script or test that calls the real code and fails loud if you're wrong.
5. You reproduced it in the running app (the repo's `verify-*` skill, if it has one).

Step 4 is usually one small script that imports the same library the app ships and calls the exact function you're worried about.

## Steps

1. **Read the change** — the diff, the symbols it adds, changes, and deletes, and what it now does differently, including what the diff doesn't spell out. Pull the PR and commit messages for intent.
2. **Find the one fact it's safe because of.** Most risky-looking changes are safe because of a single fact ("this call only drops already-dead cache entries"). If it holds, most risky cases clear at once. Spend your time here, not on a long list of maybes.
3. **Look where grep stops.** Read the source of the library you call at its pinned version, plus any local patch (`patches/`, `patch-package`). Work out when things run: microtasks, effects and unmount, app background/foreground. Follow what a symbol search misses: JSON an API returns, a DB column, a wire format, another language reading the same bytes, a feature flag, code three hops downstream.
4. **Be honest about each risk** — a real chance of happening and a real cost if it does. Keep the confirmed ones; list checked-and-cleared ones separately. Cite real `file:line`; a search that finds nothing is still an answer; never invent a caller or an API.
5. **Prove the one fact** — write the script or test, run it, paste what happened. Scratch scripts go in a temp dir, not the repo.

## Reply

- **What it does** — including the part that isn't obvious.
- **The one fact it's safe because of** — stated, the step it reached, and the proof. If you couldn't prove it, write `unproven`.
- **Risks** — how it breaks, `file:line`, how likely and how bad, how to check.
- **Cleared** — what you checked and why it's fine.
- **Before you merge** — the cheapest test or repro that catches the real bug, including the script you wrote.
