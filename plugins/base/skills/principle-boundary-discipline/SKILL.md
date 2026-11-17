---
name: principle-boundary-discipline
description: "Apply when wiring validation, error handling, or framework adapters. Concentrate guards at system boundaries (CLI, config, network, external APIs); trust internal types and keep business logic in pure functions."
disable-model-invocation: true
---

# Boundary Discipline

<!-- gbase:pstack-sync — cursor/plugins pstack `principle-boundary-discipline` 스킬을 그대로 따라가는 생성본 (MIT, Copyright (c) 2026 Lauren Tan). 직접 고치지 않는다: `python3 scripts/pstack-sync.py --apply`가 덮어쓴다. -->

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다. 코드·경로·명령어·스킬/툴 이름·상태 라벨은 그대로 둔다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## gbase

Read [pstack-adapter.md](../../references/pstack-adapter.md) once per session before you follow this skill. It maps the Cursor names below to Claude Code and gbase, and says how to run another skill this one names.

Validate, narrow types, and handle errors where data crosses a system boundary (CLI args, config files, external APIs, network). Inside, trust the types: no re-validation and no redundant nil checks. Parse raw data into domain types at the boundary, and keep transport and framework types out of the public surface. Business logic lives in pure functions with no framework dependencies. The shell that calls them is thin.

Two tests. Is this data crossing a boundary right now? If not, the validation is redundant. Can this be a pure function the shell just calls? If yes, extract it.
