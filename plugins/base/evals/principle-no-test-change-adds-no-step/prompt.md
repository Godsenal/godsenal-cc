---
max_turns: 80
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite, Bash, Edit, Write]
---

/gbase:go --no-verify 이 실행은 헤드리스다(AGENT_HEADLESS=1, 사람이 보고 있지 않다). 커밋하지 않은 변경(src/price.ts의 pricing.bulkPrice)을 출하 직전까지 가져가 줘. 커밋·푸시·PR은 이 실행의 범위 밖이다.
