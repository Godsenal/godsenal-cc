---
name: principle-minimize-reader-load
description: "Apply when reviewing or shaping code that's hard to trace. Count layers between question and answer, and hidden state in the reader's head; collapse one-caller wrappers and shrink mutable scope."
disable-model-invocation: true
---

# Minimize Reader Load

<!-- gbase:pstack-sync — cursor/plugins pstack `principle-minimize-reader-load` 스킬을 그대로 따라가는 생성본 (MIT, Copyright (c) 2026 Lauren Tan). 직접 고치지 않는다: `python3 scripts/pstack-sync.py --apply`가 덮어쓴다. -->

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다. 코드·경로·명령어·스킬/툴 이름·상태 라벨은 그대로 둔다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## gbase

Read [pstack-adapter.md](../../references/pstack-adapter.md) once per session before you follow this skill. It maps the Cursor names below to Claude Code and gbase, and says how to run another skill this one names.

Reader load is the work a reader must do to understand code. It has two independent axes: layers to trace between the question and the answer, and hidden or mutable state to hold in their head. Guard both.

- Collapse layers that only forward: wrappers with one caller, adapters with no second implementation, pass-through methods. Inline them.
- Shrink state scope: returns over mutations, locals over fields, fields over module state, module state over globals. Derive instead of sync.
- Name an invariant once at the boundary, not in every consumer.

The test: can a new reader answer "where does X come from?" and "what can change X?" in under 30 seconds? If not, cut layers or cut state.
