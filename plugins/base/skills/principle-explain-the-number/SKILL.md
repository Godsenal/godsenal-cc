---
name: principle-explain-the-number
description: "Apply before you measure, and before you trust, report, or act on a number you measured: a speedup, a regression, a throughput, a latency, or an eval result. Find what limits it, and rule out that it measured something other than the work you think."
disable-model-invocation: true
---

# Explain the Number

<!-- gbase:pstack-sync — cursor/plugins pstack `principle-explain-the-number` 스킬을 그대로 따라가는 생성본 (MIT, Copyright (c) 2026 Lauren Tan). 직접 고치지 않는다: `python3 scripts/pstack-sync.py --apply`가 덮어쓴다. -->

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다. 코드·경로·명령어·스킬/툴 이름·상태 라벨은 그대로 둔다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## gbase

Read [pstack-adapter.md](../../references/pstack-adapter.md) once per session before you follow this skill. It maps the Cursor names below to Claude Code and gbase, and says how to run another skill this one names.

- **Write the decision before you run.** Name the result that would change it, and the noise floor. Stop when the run-to-run spread is larger than the effect.
- **Ask "why not double?"** Name the resource or code path that bounds the result, from a profile or counters taken during a run. A guess from reading the code is not a limiter.
- **List what else the number could be measuring** (errors, skipped or cached work, code that never ran, an untuned side, noise, a piece too small to matter) and rule out each one with evidence.
- **Keep the run count, the spread, and the limiter with the number.**

For a performance number, run the [benchmark-checklist](../benchmark-checklist/SKILL.md) skill. For an eval result, ask whether every run did the task, whether the gap holds across trials and models, and whether the scenario matters.
