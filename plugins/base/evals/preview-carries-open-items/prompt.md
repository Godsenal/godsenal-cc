---
max_turns: 80
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite, Bash, Edit, Write, AskUserQuestion]
---

/gbase:branch-pr Risk: medium — 배송비 계산 코드; Verification: verify: node check.mjs → pass | behavior: skip — 장바구니 화면의 배송비 표시: 이 환경에 브라우저가 없어 화면을 열지 못함; Deferred: medium · introduced · src/shipping.mjs:5 · 소계가 정확히 50,000원일 때 무료 배송인지(이상인지 초과인지) 기획 확인이 안 됨 (이 샌드박스는 `.git/` 아래에 파일을 쓰지 못하게 막는다. PR 본문 초안은 `$TMPDIR/pr-body.md`에 쓴다.)
