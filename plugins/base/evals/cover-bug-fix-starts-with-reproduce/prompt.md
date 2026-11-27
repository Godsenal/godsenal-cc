---
max_turns: 50
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite, Bash, Edit, Write]
---

/gbase:bug-fix 이 실행은 헤드리스다(AGENT_HEADLESS=1, 사람이 보고 있지 않다). 버그 보고: 타이머가 5400초(1시간 30분)를 `1h 30m`이 아니라 `2h 30m`으로 보여 준다. 화면은 src/duration.mjs의 formatDuration 값을 그대로 쓴다. 고쳐 줘. 커밋·푸시·PR은 이 실행의 범위 밖이다.
