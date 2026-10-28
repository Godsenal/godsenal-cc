---
name: content-common
description: >-
  Holds the user-confirmed rules for every piece of content the gshorts harness makes — shorts, Instagram
  card news, and any account name, bio, caption, script, or post copy — chiefly that it is written from
  high-performing references actually opened on the target platform (X, Instagram, YouTube), and that every
  mistake or lesson is written into this plugin the same turn so other bots don't repeat it. Use before naming an account, writing a bio, caption, card, or script, when
  the user gives feedback that applies across formats, or when a gshorts skill points here.
---

# content-common — rules for every piece of content

Applies to everything gshorts makes. Video-wide rules live in [shorts-common](../shorts-common/SKILL.md), Instagram card news in [instagram-card-news](../instagram-card-news/SKILL.md); both point here. When they disagree, the newer dated feedback wins.

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 샘플 비교 설명, 리포트)와 콘텐츠 산출물(이름, 소개글, 캡션, 카드 문구, 대본)은 **한국어**로 쓴다. 따옴표 안 한국어는 사용자 피드백 원문 인용이므로 번역하지 않는다. 코드·경로·명령어·환경변수 이름과 커밋 메시지는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Rules for every piece of content (user-confirmed)

Quotes are the user's words with the date they were said.

- **Written from real references** — 2026-10-28 "항상 이런 컨텐츠 관련은 x나 인스타 유튜브등 적절한 플랫폼에 있는 잘나가는 레퍼런스를 기반으로": applies to every content judgment and every line of copy — names, bios, captions, card news, scripts. First open references that actually perform well on that platform (X, Instagram, YouTube, whichever the content is for), collect their original text, then write from it. Note the references (URL + the quoted original) in the work folder's report. If the references can't be opened (timeout, login wall), stop and say so; don't write from memory.
- **Made-up numbers and scope are assumptions, reported first** — 2026-10-28 "왜 주 4회임?" (a "월·수·금·일 아침 7시 반" schedule Claude Code had planned on its own went straight into the bio), 2026-10-28 "해외 AI회사라고 할 필요가 있나 … 왤케좁혀?": a number, schedule, or scope (N posts a week, a time, a narrowed audience) that comes from neither the references nor a user decision goes at the top of the report as a `가정:` line, and stays out of public copy (bio, caption, cards) until the user confirms it. Anything else the task didn't ask for is reported the same way, as one tiktok report did unprompted: "2줄째에 시리즈 안내 줄 … 을 새로 넣었는데, 이건 지시에 없던 추가야."
- **References win over the task's style conditions** — 2026-10-28 "너무구린거같은데": a "줄 앞 이모지 금지" condition in the task went against the references (an emoji per line, short memo tone) and pulled the cards away from them. When a style condition in the task contradicts the references collected, follow the references and write the conflict in the report.
- **Mistakes are recorded the same turn** — 2026-10-28 "똑같은 실수가 여러봇들에서 반복되지않게": several bots run this harness, so a mistake one makes or a lesson one learns is written into this plugin within that turn, at the place the feedback intake below points to — never only in a chat reply or a bot's own memory.

## Feedback intake — same turn, every time

Every new piece of user feedback or lesson is written into a skill **before** continuing the work:

1. Classify it: every piece of content → this file's rules; every video → shorts-common's "Rules for every video"; one format → that format skill (`foreign-clip-short`, `top3-compilation-short`, `instagram-card-news`); a new format → a new `skills/<format>/SKILL.md` that points here (and at shorts-common if it's a video).
2. Write it as a rule with the date and the user's own words in quotes (`2026-10-28 "지금 좀 ai같은데": …`). If it contradicts an existing rule, rewrite that rule with the new date instead of adding a second one.
3. Then update the pipeline or tooling default it implies, if any.

Edit the gshorts source in the godsenal-cc checkout (`plugins/shorts/skills/…`; on the reference machine `$HOME/LTH/godsenal-cc`), not the installed plugin cache — the cache is overwritten on update. Bump the gshorts version in both `plugins/shorts/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (patch for a rule, minor for a new format skill); installed copies only change once it ships.
