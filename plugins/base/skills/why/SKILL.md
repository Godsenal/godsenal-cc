---
name: why
description: "Investigates why code is the way it is — design rationale, a tradeoff, a regression's origin, a magic number, defensive code — by anchoring on git blame and PR history, then querying every connected evidence source (issue tracker, docs, chat, error tracking, observability, analytics MCPs) in parallel, and returning a cited answer that separates what the record says from what is inferred or unknown. Use for 'why does X work this way', 'why did we pick Y', 'when and why did this start', or before changing code whose intent is unclear. For how it works, use gbase:how."
allowed-tools: Read Glob Grep Bash Agent
---

# /gbase:why

`how` answers what the code does; `why` answers what forces shaped it. Ported from pstack's `why` (MIT); `references/` holds its epistemics framework, prompt templates, and per-source playbooks.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다. 신뢰도 라벨(Direct/Supported/Inferred/Speculative/Unknown)은 영어로 둔다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Posture

A careful, precise investigator: separate what you know from what you infer. Every claim sits in one confidence tier from `references/epistemics.md`, and its phrasing matches the tier. Don't confirm a hypothesis the user embedded in the question — treat it as one candidate. Investigators read; nothing writes.

## 1. Target and question

The target is code, a pattern, a feature, or a named decision; the question is a rationale, tradeoff, motivating edge case, external constraint, dead code, or history sweep. If vague, infer it from the conversation (open files, recent edits), state your reading, and proceed.

## 2. Code anchor

Build the seed context before spawning: paths and line ranges, key symbols, `git blame -L <start>,<end> <file>`, `git log --follow -p -- <file>`, `git log --oneline -20 -- <file>`, PR numbers from `(#1234)` subjects, and `gh pr view <n> --json title,body,author,mergedAt,labels,closingIssuesReferences,comments,reviews` for each substantive commit. This anchor goes to every investigator and the synthesizer.

## 3. Parallel investigators

Sub-agents can't resolve this skill's relative `references/` paths from the target repo, so read each template yourself and paste its text into the prompt. That includes `epistemics.md` for the synthesizer — its template says to read it, which only works if you pasted it.

**Default to the full investigation** — a complete coverage map, not a minimal one. Map the connected MCP tools (`mcp__<server>__*`) to the seven categories in `references/source-playbook.md`: source control (always — git and `gh`), issue tracker, long-form docs, team chat, observability, error tracking, analytics. PostHog covers both error tracking and analytics; a server that fits two categories goes under its primary evidence. A server that's configured but failed to connect is a gap, not a skip.

Spawn one investigator per category with a matching source, all in one message, each owning exactly one source: `subagent_type: "general-purpose"` (MCP access needs it), `model: "sonnet"`. Each prompt is `references/investigator-prompt.md` filled in, plus that category's `references/sources/<source>.md` (adapt the closest one for a different MCP), plus `references/sources/incident-postmortem.md` when the target looks defensive (null checks, retries, timeouts, rate limits, flags, OOM guards), plus the anchor and the question.

Skip a category only with a written reason that goes in Sources Consulted: no matching source connected, or provably irrelevant (e.g. error tracking for a build-time script).

## 4. Synthesize

One synthesizer on the session's model (omit `model`) with every finding (nulls and skips included), the anchor, the question, `references/epistemics.md`, and `references/synthesizer-prompt.md`.

## 5. Present

Present its output; light edits only, and **don't rewrite the confidence language**. Sections: The Question, The Code in Question, What We Found, What We Can Reasonably Infer, Competing Hypotheses, What We Don't Know, Sources Consulted (one line per category, including empty and skipped ones with the reason), Confidence Summary. If the question precedes a change, end with a Preserve / Change / Avoid / Risk constraint set.

The common failure is recency bias — the current shape is usually many earlier decisions accreted, so trace back past the last commit.
