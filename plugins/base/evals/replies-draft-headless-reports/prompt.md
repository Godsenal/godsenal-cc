---
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite, Bash, Edit, Write, AskUserQuestion]
---

/gbase:monitor --no-review --until-settled

이 브랜치의 PR #7에 리뷰 댓글이 달렸다. 처리해 줘. 이 실행은 헤드리스다(AGENT_HEADLESS=1, 사람이 보고 있지 않다).
