---
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Edit, Write, TodoWrite]
---

/gbase:work 설정 항목 저장을 fetch 직접 호출에서 로컬 캐시 + 동기화 큐 구조로 옮기려고 해. 한 번에 못 하니까 PR 여러 개로 쌓아서 단계별로 진행할 거야. 단계별 계획 파일(docs/plan-sync.md)을 쓰고 첫 단계만 구현해. 커밋이나 PR은 하지 마.
