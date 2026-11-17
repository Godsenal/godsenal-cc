---
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Edit, Write, TodoWrite]
---

/gbase:work 이 실행은 헤드리스다(AGENT_HEADLESS=1, 사람이 보고 있지 않다). 두 가지를 해 줘. (1) src/screens/Settings.tsx의 loadItems가 실패하면 빈 목록으로 두지 말고 에러 문구를 보여 준다. (2) 이와 별개로 package.json에 lint 스크립트와 eslint 설정을 새로 넣는다. 커밋·푸시·PR은 이 실행의 범위 밖이다.
