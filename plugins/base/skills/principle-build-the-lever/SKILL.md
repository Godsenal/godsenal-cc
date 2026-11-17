---
name: principle-build-the-lever
description: "Apply to any non-trivial work, not just bulk work: edits, migrations, analyses, checks. Build the tool that does it or proves it (codemod, script, generator, or a skill your subagents follow) instead of working by hand. The tool is the artifact a reviewer can rerun."
disable-model-invocation: true
---

# Build the Lever

<!-- gbase:pstack-sync — cursor/plugins pstack `principle-build-the-lever` 스킬을 그대로 따라가는 생성본 (MIT, Copyright (c) 2026 Lauren Tan). 직접 고치지 않는다: `python3 scripts/pstack-sync.py --apply`가 덮어쓴다. -->

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다. 코드·경로·명령어·스킬/툴 이름·상태 라벨은 그대로 둔다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## gbase

Read [pstack-adapter.md](../../references/pstack-adapter.md) once per session before you follow this skill. It maps the Cursor names below to Claude Code and gbase, and says how to run another skill this one names.

When the work isn't trivial, build the tool that does it (a codemod, script, generator, or rerunnable check) instead of doing it by hand. The bar is triviality, not repetition. Skip the tool only for a couple of obvious edits.

- Do the first unit by hand, then build the tool and prove it by rerunning it on that unit. Make it safe to rerun.
- A deterministic tool beats fan-out. When you do fan out, write the recipe, the verification contract, and the fences as one skill the delegates read and cannot edit.
- Applying this produces a file. No script, codemod, generator, or delegate skill in the diff means you didn't apply it. Commit it when the work outlives the session.
- Build the smallest script that does or proves the job, never a framework.
