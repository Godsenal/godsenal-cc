---
max_turns: 60
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
---

/gbase:go --no-review --no-verify 이 실행은 헤드리스다(AGENT_HEADLESS=1, 사람이 보고 있지 않다). src/cart.ts의 커밋하지 않은 변경을 출하 직전까지 다듬어 줘. 커밋·푸시·PR은 이 실행의 범위 밖이다.
