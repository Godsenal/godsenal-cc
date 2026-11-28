---
name: how
description: "Explains how a part of the codebase works (architecture, runtime flow, where things live) from real files and functions, and answers placement and ownership questions ('where should this live', 'which module owns this', 'is this the right layer'). Use for 'how does X work', walking a flow before changing it, or onboarding ('어떻게 동작해?', '흐름 설명해 줘'). For why it was built that way, gbase:why."
allowed-tools: Read Glob Grep Bash Agent
---

# /gbase:how

Answer "how does X work?" with an explanation a senior engineer can build a working mental model from — not annotated source code. Ported from pstack's `how` (MIT); the prompt templates in `references/` are pstack's.

## 출력 언어

사용자에게 보이는 글은 **한국어**로 쓰고, 코드·명령·상태 라벨·커밋·브랜치는 레포 관례를 따른다. 세부: [output-language.md](../../references/output-language.md).

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
