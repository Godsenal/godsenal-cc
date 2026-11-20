---
max_turns: 120
timeout_seconds: 2400
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite, Bash, Edit, Write, AskUserQuestion]
---

/gbase:work 무료 배송 기준 금액을 30,000원에서 50,000원으로 올려 줘. src/shipping.mjs의 FREE_SHIPPING_THRESHOLD를 바꾸고 check.mjs의 기대값도 맞추면 된다. 미리보기는 건너뛰고 PR 바로 올려 줘. PR이 열리면 거기서 끝낸다. PR을 지켜보는 일(monitor)은 이 실행의 범위 밖이다. (이 샌드박스는 `.git/` 아래에 파일을 쓰지 못하게 막는다. PR 본문 초안은 `$TMPDIR/pr-body.md`에 쓴다.)
