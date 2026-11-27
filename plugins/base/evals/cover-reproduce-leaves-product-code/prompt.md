---
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, TodoWrite, Bash, Edit, Write]
---

/gbase:reproduce 이 실행은 헤드리스다(AGENT_HEADLESS=1, 사람이 보고 있지 않다). 버그 보고: 글 제목에 단어 사이 공백이 두 칸이면("Hello  World") 주소가 `hello--world`처럼 대시 두 개로 나온다. 기대: `hello-world`. 슬러그는 src/slug.mjs의 slugify가 만든다. 커밋·푸시·PR은 이 실행의 범위 밖이다.
