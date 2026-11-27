---
max_turns: 50
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite, Bash, Write]
---

/gbase:plan 이 실행은 헤드리스다(AGENT_HEADLESS=1, 사람이 보고 있지 않다). 아이디어: 이 메모 CLI에 태그를 붙이고, 태그로 걸러 보고, 나중에는 태그 하나에 묶인 메모를 다른 사람과 공유하고 싶다. (이 샌드박스는 작업 디렉터리 밖에 Write 도구로 쓰지 못한다. GBASE_HOME은 이 디렉터리의 `.gbase`로 본다.)
