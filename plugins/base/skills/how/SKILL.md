---
name: how
description: "Explains how a part of the codebase works — subsystem architecture, runtime flow, where things live — at the level a senior engineer needs to start working in it, citing real files and functions. Also answers placement and ownership questions ('where should this live', 'which module owns this', 'is this the right layer'). Use for 'how does X work', a walkthrough before changing something, or onboarding onto an area. For why it was built that way, use gbase:why."
allowed-tools: Read Glob Grep Bash Agent
---

# /gbase:how

Answer "how does X work?" with an explanation a senior engineer can build a working mental model from — not annotated source code. Ported from pstack's `how` (MIT); the prompt templates in `references/` are pstack's.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인, `AskUserQuestion`의 질문·헤더·옵션·설명까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드(`critical`/`high`/`medium`/`low`, `PASS`/`FAIL`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름 — 이건 레포의 기존 관례(`git log`)를 따른다. PR 제목·본문은 기본 **한국어**로 쓴다 — 섹션 제목 같은 템플릿 라벨은 영어로 두고, 레포가 분명히 다른 언어로 PR을 써 왔거나(예: 영어 오픈소스) 사용자가 요청하면 그 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## 1. Assess complexity

If the scope is ambiguous, state your interpretation and explore; the user can redirect. When in doubt, take the simple path.

- **Simple** — one module, a small utility, a narrow "how does function X work": answer directly in this thread, following `references/explainer-prompt.md`'s output format without the explorer-findings section. (pstack spawns one explainer here; in Claude Code the main agent can read a few files itself.)
- **Complex** — a subsystem across files or services, a cross-cutting feature, an architectural overview: go to step 2.

## 2. Explore (complex only)

Sub-agents can't resolve this skill's relative `references/` paths from the target repo, so read each template yourself and paste its text into the prompt.

Split the question into 2–4 angles, each a distinct slice. Spawn all explorers in one message — `subagent_type: "Explore"` (read-only), `model: "sonnet"` — each with `references/explorer-prompt.md` and its angle filled in.

## 3. Synthesize (complex only)

Once every explorer returns, spawn one explainer on the session's model (omit `model`) with `references/explainer-prompt.md` and all findings filled in. It reconciles overlaps and checks contradictions against the code.

## 4. Present

Present the explanation with light edits only. Sections, dropping any that don't apply: Overview, Key Concepts, How It Works, Where Things Live, Gotchas. A `mermaid` diagram only where the flow crosses components.
